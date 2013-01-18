from cStringIO import StringIO
from jinja2 import contextfunction
import base64
import glob
import Image
import os
import re
import math

# Entropy, etc. code lifted from Easy-Thumbnails. Thanks.


def image_entropy(im):
	"""
	Calculate the entropy of an image. Used for "smart cropping".
	"""
	if not isinstance(im, Image.Image):
		# Can only deal with PIL images. Fall back to a constant entropy.
		return 0
	hist = im.histogram()
	hist_size = float(sum(hist))
	hist = [h / hist_size for h in hist]
	return -sum([p * math.log(p, 2) for p in hist if p != 0])

def _compare_entropy(start_slice, end_slice, slice, difference):
	start_entropy = image_entropy(start_slice)
	end_entropy = image_entropy(end_slice)
	if end_entropy and abs(start_entropy / end_entropy - 1) < 0.01:
		# Less than 1% difference, remove from both sides.
		if difference >= slice * 2:
			return slice, slice
		half_slice = slice // 2
		return half_slice, slice - half_slice
	if start_entropy > end_entropy:
		return 0, slice
	else:
		return slice, 0

def scale_and_crop(im, size, crop=False, upscale=False, **kwargs):
	source_x, source_y = [float(v) for v in im.size]
	target_x, target_y = [float(v) for v in size]

	if crop or not target_x or not target_y:
		scale = max(target_x / source_x, target_y / source_y)
	else:
		scale = min(target_x / source_x, target_y / source_y)

	# Handle one-dimensional targets.
	if not target_x:
		target_x = source_x * scale
	elif not target_y:
		target_y = source_y * scale

	if scale < 1.0 or (scale > 1.0 and upscale):
		# Resize the image to the target size boundary. Round the scaled
		# boundary sizes to avoid floating point errors.
		im = im.resize((int(round(source_x * scale)),
						int(round(source_y * scale))),
					   resample=Image.ANTIALIAS)

	if crop:
		# Use integer values now.
		source_x, source_y = im.size
		# Difference between new image size and requested size.
		diff_x = int(source_x - min(source_x, target_x))
		diff_y = int(source_y - min(source_y, target_y))
		if diff_x or diff_y:
			# Center cropping (default).
			halfdiff_x, halfdiff_y = diff_x // 2, diff_y // 2
			box = [halfdiff_x, halfdiff_y,
				   min(source_x, int(target_x) + halfdiff_x),
				   min(source_y, int(target_y) + halfdiff_y)]
			# See if an edge cropping argument was provided.
			edge_crop = (isinstance(crop, basestring) and
						 re.match(r'(?:(-?)(\d+))?,(?:(-?)(\d+))?$', crop))
			if edge_crop and filter(None, edge_crop.groups()):
				x_right, x_crop, y_bottom, y_crop = edge_crop.groups()
				if x_crop:
					offset = min(int(target_x) * int(x_crop) // 100, diff_x)
					if x_right:
						box[0] = diff_x - offset
						box[2] = source_x - offset
					else:
						box[0] = offset
						box[2] = source_x - (diff_x - offset)
				if y_crop:
					offset = min(int(target_y) * int(y_crop) // 100, diff_y)
					if y_bottom:
						box[1] = diff_y - offset
						box[3] = source_y - offset
					else:
						box[1] = offset
						box[3] = source_y - (diff_y - offset)
			# See if the image should be "smart cropped".
			elif crop == 'smart':
				left = top = 0
				right, bottom = source_x, source_y
				while diff_x:
					slice = min(diff_x, max(diff_x // 5, 10))
					start = im.crop((left, 0, left + slice, source_y))
					end = im.crop((right - slice, 0, right, source_y))
					add, remove = _compare_entropy(start, end, slice, diff_x)
					left += add
					right -= remove
					diff_x = diff_x - add - remove
				while diff_y:
					slice = min(diff_y, max(diff_y // 5, 10))
					start = im.crop((0, top, source_x, top + slice))
					end = im.crop((0, bottom - slice, source_x, bottom))
					add, remove = _compare_entropy(start, end, slice, diff_y)
					top += add
					bottom -= remove
					diff_y = diff_y - add - remove
				box = (left, top, right, bottom)
			# Finally, crop the image!
			if crop != 'scale':
				im = im.crop(box)
	return im


@contextfunction
def render_gallery(context, static_subfolder, thumb_size=128, thumb_quality=50):
	project = context["project"]

	output = []

	for filename in sorted(glob.glob(os.path.join(project.static_path, static_subfolder, "*.jpg"))):
		src_image = Image.open(filename).convert("RGB")
		thumb_image = scale_and_crop(src_image, (thumb_size, thumb_size), crop="smart")
		sio = StringIO()
		thumb_image.save(sio, format="jpeg", quality=thumb_quality)
		thumb_data = "data:image/jpeg;base64,%s" % base64.b64encode(sio.getvalue())
		output.append({
			"name":	os.path.basename(filename),
			"thumb_data": thumb_data,
			"url":	"/".join([context["STATIC"], static_subfolder, os.path.basename(filename)])
		})

	return output