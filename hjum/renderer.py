class RendererRegistry(object):
	def __init__(self):
		self.registry = {}

	def register(self, extensions, klass):
		if isinstance(extensions, basestring):
			extensions = (extensions, )
		for ext in extensions:
			self.registry[ext.lower()] = klass

	def get(self, extension):
		return self.registry.get(extension.lower())

renderer_registry = RendererRegistry()


def discover_renderers():
	import os, glob
	for fname in glob.glob(os.path.join(os.path.dirname(__file__), "renderers", "*.py")):
		basename = os.path.splitext(os.path.basename(fname))[0]
		module = __import__("hjum.renderers.%s" % basename)


class Renderer(object):
	def __init__(self, project):
		self.project = project

	def render_to_html(self, page):
		raise NotImplementedError("Not implemented")

class RawRenderer(Renderer):
	def render_to_html(self):
		return self.page


renderer_registry.register(("html", "htm"), RawRenderer)

def import_if_available(module_name):
	try:
		return (__import__(module_name), None)
	except ImportError, ie:
		return (None, ie.message)

#########################################################################################
## Textile

textile, textile_error = import_if_available("textile")

class TextileRenderer(Renderer):
	def render_to_html(self, page):
		if not textile:
			raise ValueError("Textile rendering not available: %s" % textile_error)

		return textile.textile(page.source)

renderer_registry.register("tx", TextileRenderer)

#########################################################################################
## Markdown

markdown, markdown_error = import_if_available("markdown")

class MarkdownRenderer(Renderer):
	def render_to_html(self, page):
		if not markdown:
			raise ValueError("Markdown rendering not available: %s" % markdown_error)

		return markdown.markdown(page.source, output_format="html5")

renderer_registry.register("md", MarkdownRenderer)		