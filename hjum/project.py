from hjum.page import Page
import jinja2
import os
import re
import urlparse
import logging
import shutil

ref_re = re.compile(r"""(href|src)=['"]?(.+?)['">]""", re.I)

log = logging.getLogger("Project")

class Project(object):
	def __init__(self, base_path):
		self.base_path = os.path.realpath(base_path)
		self.template_path = os.path.join(base_path, "templates")
		self.content_path = os.path.join(base_path, "content")
		self.static_path = os.path.join(base_path, "static")
		self.output_path = os.path.join(base_path, "output")
		self.output_static_path = os.path.join(base_path, "output", "static")
		self.jinja_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(self.template_path))
		self.pages = {}
		self.top_level_pages = []

	def init(self):
		for dir in (self.template_path, self.content_path, self.static_path, self.output_path, self.output_static_path):
			if not os.path.isdir(dir):
				os.makedirs(dir)
		page_template = os.path.join(self.template_path, "page.jinja2")
		if not os.path.isfile(page_template):
			from hjum.defaults import default_page_template
			with file(page_template, "wb") as out_f:
				out_f.write(default_page_template.encode("UTF-8"))


	def load(self):
		self.pages = dict((page.name, page) for page in self.get_pages())
		for page in self.pages.itervalues():
			parents = page.name.split("/")[:-1]
			page.parent = self.pages.get(parents[-1] if parents else "")
			if page.parent:
				page.parent.children[page.name] = page
		self.top_level_pages = [page for page in self.pages.itervalues() if not page.parent]


	def get_pages(self):
		for dirpath, dirnames, filenames in os.walk(self.content_path):
			for filename in filenames:
				basename = os.path.splitext(filename)[0]
				if basename == "index":
					name = dirpath
				else:
					name = dirpath + "/" + basename
				name = name.replace(self.content_path, "").strip("/\\")
				source_filename = os.path.join(dirpath, filename)
				yield Page(self, name, source_filename)

	def wrap_in_template(self, page):
		template = self.jinja_env.get_template(page.template_name + ".jinja2")
		static_path = "/".join(([".."] * page.name.count("/")) + ["static"])

		return template.render({
			"content": jinja2.Markup(page.rendered_content),
			"page": page,
			"parent": page.parent,
			"project": self,
			"siblings": page.get_siblings(),
			"children": page.children.itervalues(),
			"STATIC": static_path,
			"title": page.get_title(),
			"url": page.target_filename,
			"top_level_pages": self.top_level_pages,
		})

	def find_link_page(self, page, loc):
		ret_page = self.pages.get(loc)
		if ret_page:
			return ret_page

		try_names = [loc]
		if page.parent:
			ret_page = self.pages.get(page.parent.name + "/" + loc)
			if ret_page:
				return ret_page

		for ret_page in self.pages.itervalues():
			if ret_page.basename == loc:
				return ret_page

		return None


	def rewrite_links(self, page, content):
		def rewrite_link(match):
			attr, loc = match.groups()
			parsed = urlparse.urlparse(loc)
			if not parsed.netloc:
				other_page = self.find_link_page(page, loc)
				if other_page:
					loc = page.relative_url(other_page)
				else:
					logging.warn("Unable to rewrite link %s on page %s, no page could be found: %r", match.group(0), page.name, try_names)
			return "%s=\"%s\"" % (attr, loc)
			
		return ref_re.sub(rewrite_link, content)

	def copy_static(self, force_copy=False):
		for dirpath, dirnames, filenames in os.walk(self.static_path):
			for filename in filenames:
				source_filename = os.path.join(dirpath, filename)
				source_stat = os.stat(source_filename)
				target_filename = os.path.normpath(os.path.join(self.output_static_path, os.path.relpath(dirpath, self.static_path), filename))
				if not force_copy and os.path.exists(target_filename):
					target_stat = os.stat(target_filename)
					if target_stat.st_mtime <= source_stat.st_mtime and target_stat.st_size == source_stat.st_size:
						continue # skip!
				target_dir = os.path.dirname(target_filename)
				if not os.path.isdir(target_dir):
					log.debug("Creating directory %s" % target_dir)
					os.makedirs(target_dir)
				shutil.copy2(source_filename, target_filename)
				yield target_filename