from hjum.project import Project
from hjum.renderer import discover_renderers
import argparse
import logging
import os

log = logging.getLogger("hjum")

def cmdline():
	ap = argparse.ArgumentParser()
	ap.add_argument("--init", action="store_const", dest="action", const="init")
	ap.add_argument("project")
	ap.add_argument("--force", "-f", action="store_true", default=False)
	ap.add_argument("--verbose", "-v", action="store_true", default=False)
	ap.add_argument("--debug", "-d", action="store_true", default=False)
	ap.add_argument("--copy-static", "-s", action="store_true", default=False)

	args = ap.parse_args()
	if args.debug:
		log_level = logging.DEBUG
	elif args.verbose:
		log_level = logging.INFO
	else:
		log_level = logging.WARN
	logging.basicConfig(level=log_level)

	discover_renderers()
	project = Project(args.project)

	if args.action == "init":
		project.init()
		print "Project initialized at %s" % project.base_path
		return

	if not os.path.isdir(project.base_path):
		ap.error("%s is not a directory" % project_dir)

	project.load()
	log.info("%d pages read.", len(project.pages))

	written = set()
	for page in project.pages.itervalues():
		if page.process(force_write=args.force):
			written.add(page)

	log.info("%d output pages written.", len(written))

	if args.copy_static:
		n = len(list(project.copy_static(force_copy=args.force)))
		log.info("%d static files copied.", n)

if __name__ == '__main__':
	cmdline()