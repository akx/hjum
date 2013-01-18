from hjum.renderer import renderer_registry
from hjum.utils import read_flags
import codecs
import hashlib
import os
import re
import posixpath	
import logging

header_re = re.compile("<h([1-6])>(.+?)<", re.I)

log = logging.getLogger("Page")

class Page(object):
	def __init__(self, project, name, source_filename):
		self.project = project
		self.name = (name or "index")
		self.basename = name.split("/")[-1]
		self.source_filename = source_filename
		self.target_filename = (self.name or "index") + ".html"
		self.extension = os.path.splitext(source_filename)[1].strip(".").lower()

		self.parent = None
		self.children = {}
		self.flags = {}
		self.template_name = None
		self.source = None
		self.rendered_content = None
		self.rendered_with_template = None
	
	def __repr__(self):
		return "<%s %X (%s)>" % (self.__class__.__name__, id(self), self.name)

	def load(self):
		with codecs.open(self.source_filename, "rb", encoding="UTF-8") as in_f:
			data = in_f.read()
		data = data.replace("\r\n", "\n").replace("\r", "\n")
		self.source, self.flags = read_flags(data)
		self.template_name = (self.flags.get("template") or "page")

	def render(self):
		if not self.source:
			self.load()
		renderer_class = renderer_registry.get(self.extension)
		if not renderer_class:
			raise ValueError("Could not find renderer for page %r (extension %s)" % (self.name, self.extension))
		renderer = renderer_class(project=self.project)
		source = self.project.preprocess_page_content(self)
		self.rendered_content = renderer.render_to_html(page=self, source=source)
		self.rendered_with_template = self.project.wrap_in_template(self)

	def write(self, force=False):
		assert (self.rendered_with_template is not None)

		target_filename = os.path.join(self.project.output_path, self.target_filename)
		orig_hash = "x"
		if not force and os.path.isfile(target_filename):
			with file(target_filename, "rb") as in_f:
				orig_hash = hashlib.md5(in_f.read()).hexdigest()
		
		byte_content = self.rendered_with_template.encode("UTF-8")

		curr_hash = hashlib.md5(byte_content).hexdigest()

		if orig_hash != curr_hash:
			target_dir = os.path.dirname(target_filename)
			if not os.path.isdir(target_dir):
				os.makedirs(target_dir)
			log.info("Writing page %s to %s", self.name, target_filename)
			with file(target_filename, "wb") as out_f:
				out_f.write(byte_content)
			return True
		else:
			return False

	def process(self, force_write=False):
		self.render()
		return self.write(force=force_write)

	def get_siblings(self):
		return (self.parent.children.itervalues() if self.parent else [])

	def relative_url(self, other_page):
		return posixpath.relpath(other_page.target_filename, start=posixpath.dirname(self.target_filename))

	def get_headers(self):
		assert self.rendered_content
		return [(int(m.group(1)), m.group(2)) for m in header_re.finditer(self.rendered_content)]

	def get_title(self):
		if not self.rendered_content:
			return ""
		title = self.flags.get("title")
		if title and isinstance(title, basestring):
			return title
		else:
			headers = self.get_headers()
			headers.sort()
			return (headers[0][1] if headers else u"")
