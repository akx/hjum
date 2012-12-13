import re

FLAG_RE = re.compile(r"^//\s*([a-zA-Z-_]+)\s*?(.*)$", re.MULTILINE)

def read_flags(data):
	flags = dict()
	
	def set_flag(match):
		flags[match.group(1)] = ((match.group(2) or "").strip() or True)
		return ""

	data = FLAG_RE.sub(set_flag, data)
	data = data.strip()
	return (data, flags)
