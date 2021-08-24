from psd_tools import PSDImage
from PIL import Image, ImageDraw, ImageFont
import sys, os, shutil, random, glob
import PostingHelper

# HELPERS -----------------------------------------------

def getNumPanels(rawComicImage, panelWidth):
	width, height = rawComicImage.size
	return int(width / panelWidth)

def fillImage(image, color):
	alpha = image.getchannel('A')
	filledImage = Image.new('RGBA', image.size, color=color)
	filledImage.putalpha(alpha)
	return filledImage

def addBorder(image, panelWidth, borderWidth, xVal=0):
	borderImage = Image.new('RGBA', image.size)
	draw = ImageDraw.Draw(borderImage)
	draw.rectangle([xVal * panelWidth, 0, (xVal + 1) * panelWidth, panelWidth], fill=None, outline="black", width=borderWidth)
	image = Image.alpha_composite(image, borderImage)
	return image

# resize image but keep aspect ratio the same based on the height
def resizeImageByHeight(image, baseHeight):
	width, height = image.size
	hPercent = (baseHeight / float(height))
	wSize = int((float(width) * float(hPercent)))
	return image.resize((wSize, baseHeight), Image.ANTIALIAS)

# resize image with same aspect ratio based on the width
def resizeImageByWidth(image, baseWidth):
	width, height = image.size
	wPercent = (baseWidth / float(width))
	hSize = int((float(height) * float(wPercent)))
	return image.resize((baseWidth, hSize), Image.ANTIALIAS)

# Image Manipulation --------------------------------------------------------

def addWatermark(image, padding, xCentering, yCentering): 
	nameImage = Image.open(f'assets/watermark.png')
	signatureImage = Image.open(f'assets/signature.png')

	nameImage = resizeImageByHeight(nameImage, padding)
	signatureImage = resizeImageByHeight(signatureImage, padding)

	nameWidth, nameHeight = nameImage.size
	signatureWidth, signatureHeight = signatureImage.size
	comicWidth, comicHeight = image.size

	nameXPos = comicWidth - padding - nameWidth - xCentering
	nameYPos = comicHeight - padding - yCentering
	signatureXPos = padding + xCentering
	signatureYPos = comicHeight - padding - yCentering

	image.paste(nameImage, (nameXPos, nameYPos), nameImage)
	image.paste(signatureImage, (signatureXPos, signatureYPos), signatureImage)

	return image;

def resizePanels(panels, padding, comicWidth, comicHeight, rows, cols):
	panelWidth = panelHeight = panels[0].size
	panelType = "horizontal" if panelWidth >= panelHeight else "vertical"

	resizedWidth = int((comicWidth - (padding * (cols + 1))) / cols)
	resizedHeight = int((comicHeight - (padding * (rows + 1))) / rows)

	resizedPanels = []
	for i, panel in enumerate(panels):
		if panelType == "horizontal":
			if comicWidth >= comicHeight and cols > rows:
				panel = resizeImageByWidth(panel, resizedWidth)
			else:
				panel = resizeImageByHeight(panel, resizedHeight)
		if panelType == "vertical":
			if comicWidth <= comicHeight and cols < rows:
				panel = resizeImageByHeight(panel, resizedHeight)
			else:
				panel = resizeImageByWidth(panel, resizedWidth)
		resizedPanels.append(panel)

	return resizedPanels

def drawComic(panels, padding, comicWidth, comicHeight, rows, cols, watermark):
	if len(panels)%2 == 0 and rows * cols > len(panels):
		return Image.new("RGBA", (comicWidth, comicHeight), (255, 255, 255))
	if len(panels)%2 == 1 and (rows * cols) - 1 > len(panels):
		return Image.new("RGBA", (comicWidth, comicHeight), (255, 255, 255))

	panels = resizePanels(panels, padding, comicWidth, comicHeight, rows, cols)
	numPanels = len(panels)

	# extra settings in case of panels not being square
	# 1. get actual panel widths and actual comic size after resizing
	panelWidth, panelHeight = panels[0].size
	resizedComicWidth = (panelWidth * cols) + ((cols + 1) * padding)
	resizedComicHeight = (panelHeight * rows) + ((rows + 1) * padding) 

	# 2. Center it with spacing
	xCentering = 0
	yCentering = 0
	if resizedComicWidth < comicWidth:
		xCentering = int((comicWidth - resizedComicWidth) / 2)
	if resizedComicHeight < comicHeight:
		yCentering = int((comicHeight - resizedComicHeight) / 2)

	comicImage = Image.new("RGBA", (comicWidth, comicHeight), (255, 255, 255))

	currPanel = 0
	for i in range(rows):
		panelsRemaining = (numPanels - (currPanel + 1)) + 1 # panels remaining to draw
		if i == rows - 1 and panelsRemaining < cols:
			for r in range(panelsRemaining):
				missingPanels = cols - panelsRemaining # panels that are not in the final row
				missingWidth = int((panelWidth * missingPanels) / 2)
				missingPadding = int((padding * missingPanels) / 2)

				# xPos = half of missing panel width + half of missing panel padding, plus panels widths drawn, plus padding, plus centering
				xPos = missingWidth + missingPadding + (r * panelWidth) + ((r + 1) * padding) + xCentering
				yPos = (i * panelHeight) + ((i + 1) * padding) + yCentering
				comicImage.paste(panels[currPanel], (xPos, yPos))
				currPanel += 1
			break
		else:
			for j in range(cols):
				xPos = (j * panelWidth) + ((j + 1) * padding) + xCentering
				yPos = (i * panelHeight) + ((i + 1) * padding) + yCentering
				comicImage.paste(panels[currPanel], (xPos, yPos))
				currPanel += 1

	if watermark:
		comicImage = addWatermark(comicImage, padding, xCentering, yCentering)

	return comicImage

def createThumbnail(panels, channelName, width, height):
	chosenPanel = panels[0].resize((width, height), Image.ANTIALIAS)
	chosenPanel.save(f'outputs/{channelName}-Thumbnail.png', "PNG")

# -----------------------------------------------------
# return 2 arrays of the psd layer names and images
def getLayerImagesAndNames(psdImage):
	layerImages = []
	layerNames = []

	for layer in psdImage:
		layer.opacity = 255
		layer.visible = True
		if layer.is_group():
			for child in layer:
				layerImages.append(child.composite())
				layerNames.append(child.name)
		else:
			layerImages.append(layer.composite())
			layerNames.append(layer.name)
	return layerImages, layerNames

# returns an array of the comics panels (slices the comic based on panel width)
def getPanels(comic, panelWidth):
	width, height = comic.size
	panels = []

	xPos = 0
	while xPos < width:
		panel = comic.crop((xPos, 0, xPos + panelWidth, height))
		panels.append(panel)
		xPos += panelWidth

	return panels

def createCloseups(panels, padding, name, comicWidth, comicHeight, watermark, watermarkType):
	for i, panel in enumerate(panels):
		useWatermark = True if watermark and watermarkType == "normal" else i == len(panels) - 1 if watermark and watermarkType == "last" else False
		c = drawComic([panels[i]], padding, comicWidth, comicHeight, rows=1, cols=1, watermark=useWatermark)
		c.save(f'outputs/{name}-{str(i+1)}.png', "PNG")

def createComic(panels, padding, name, comicWidth, comicHeight, rows, cols, watermark):
	c = drawComic(panels, padding, comicWidth, comicHeight, rows, cols, watermark)
	c.save(f'outputs/{name}.png', "PNG")

def createYouTubeThumbnail(panel, titleText):
	panel = resizeImageByHeight(panel, 720)

	thumbnailImage = Image.new("RGBA", (1280, 720), (255, 255, 255))
	thumbnailImage.paste(panel, (thumbnailImage.size[0] - panel.size[0], 0), panel)

	ellipseImage = Image.new("RGBA", thumbnailImage.size)
	ellipseDraw = ImageDraw.Draw(ellipseImage)
	ellipseDraw.ellipse([(-100, -200), (660, 900)], fill="#fec3fe")
	thumbnailImage = Image.alpha_composite(thumbnailImage, ellipseImage)

	textImage = Image.new("RGBA", thumbnailImage.size)
	textDraw = ImageDraw.Draw(textImage)
	textPosition = (50, 150) if "\n" not in titleText else (50, 50)
	textDraw.multiline_text(textPosition, titleText, fill="#1B001C", font=ImageFont.truetype("assets/Montserrat-ExtraBold.ttf", 150), align="left", stroke_width=15, stroke_fill="white")
	textDraw.multiline_text((50, 450), 'NARRATED\nWEBCOMIC', fill="#1B001C", font=ImageFont.truetype("assets/Montserrat-Medium.ttf", 80), align="left")
	thumbnailImage = Image.alpha_composite(thumbnailImage, textImage)

	thumbnailImage.save(f'outputs/YouTube-Thumbnail.png', "PNG")

# -----------------------------------------------------

def ComicSlicer(fileName, titleText):
	psdImage = PSDImage.open(fileName)

	panelWidth = 1080
	padding = 35

	# comic variation images
	rawComicImage = Image.new("RGBA", psdImage.size)
	sketchOnlyImage = Image.new("RGBA", psdImage.size)
	lineartOnlyImage = Image.new("RGBA", psdImage.size)
	noTextNoBubbleImage = Image.new("RGBA", psdImage.size)
	noTextImage = Image.new("RGBA", psdImage.size)

	numPanels = getNumPanels(rawComicImage, panelWidth)
	layerImages, layerNames = getLayerImagesAndNames(psdImage)

	# fill all images with correct variations
	for i, layerImage in enumerate(layerImages):
		if "Layer" in layerNames[i]:
			rawComicImage = Image.alpha_composite(rawComicImage, layerImage)

		if "Sketch" in layerNames[i]:
			sketchOnlyImage = Image.alpha_composite(sketchOnlyImage, fillImage(layerImage, "black"))

		if "Text" in layerNames[i]:
			rawComicImage = Image.alpha_composite(rawComicImage, layerImage)
			lineartOnlyImage = Image.alpha_composite(lineartOnlyImage, fillImage(layerImage, "black"))

		if "Outline" in layerNames[i]:
			rawComicImage = Image.alpha_composite(rawComicImage, layerImage)
			lineartOnlyImage = Image.alpha_composite(lineartOnlyImage, fillImage(layerImage, "black"))
			noTextImage = Image.alpha_composite(noTextImage, layerImage)
			if "Bubble" not in layerNames[i]:
				noTextNoBubbleImage = Image.alpha_composite(noTextNoBubbleImage, layerImage)

		if "Color" in layerNames[i]:
			rawComicImage = Image.alpha_composite(rawComicImage, layerImage)
			lineartOnlyImage = Image.alpha_composite(lineartOnlyImage, fillImage(layerImage, "white"))
			noTextImage = Image.alpha_composite(noTextImage, layerImage)
			if "Bubble" not in layerNames[i]:
				noTextNoBubbleImage = Image.alpha_composite(noTextNoBubbleImage, layerImage)

		if "Border" in layerNames[i]:
			rawComicImage = Image.alpha_composite(rawComicImage, layerImage)

		if "Panel" in layerNames[i]:
			rawComicImage = Image.alpha_composite(rawComicImage, layerImage)
			sketchOnlyImage = Image.alpha_composite(sketchOnlyImage, fillImage(layerImage, "white"))
			lineartOnlyImage = Image.alpha_composite(lineartOnlyImage, fillImage(layerImage, "white"))
			noTextImage = Image.alpha_composite(noTextImage, layerImage)
			noTextNoBubbleImage = Image.alpha_composite(noTextNoBubbleImage, layerImage)

		# draw outlines on the sketch and lineart comics
		if i == len(layerImages) - 1:
			for j in range(numPanels):
				sketchOnlyImage = addBorder(sketchOnlyImage, panelWidth, borderWidth=10, xVal=j)
				lineartOnlyImage = addBorder(lineartOnlyImage, panelWidth, borderWidth=10, xVal=j)

	rawComicPanels = getPanels(rawComicImage, panelWidth)
	sketchOnlyPanels = getPanels(sketchOnlyImage, panelWidth)
	lineartOnlyPanels = getPanels(lineartOnlyImage, panelWidth)
	noTextNoBubblePanels = getPanels(noTextNoBubbleImage, panelWidth)
	noTextPanels = getPanels(noTextImage, panelWidth)

	# SAVE COMIC VARIATIONS

	# Closeups
	createCloseups(rawComicPanels, padding, "Closeup", comicWidth=1080, comicHeight=1080, watermark=True, watermarkType="normal")

	# Webtoon
	createThumbnail(noTextNoBubblePanels, "Webtoon", width=160, height=151)
	createCloseups(rawComicPanels, padding, "Webtoon", comicWidth=800, comicHeight=800, watermark=True, watermarkType="last")
	resizeImageByWidth(Image.open(f'assets/webtoon-header.png'), 800).save(f'outputs/Webtoon-0.png', "PNG")
	resizeImageByWidth(Image.open(f'assets/webtoon-footer.png'), 800).save(f'outputs/Webtoon-{numPanels + 1}.png', "PNG")

	# Tapas
	createThumbnail(noTextNoBubblePanels, "Tapas", width=300, height=300)
	createCloseups(rawComicPanels, padding, "Tapas", comicWidth=900, comicHeight=900, watermark=True, watermarkType="last")
	resizeImageByWidth(Image.open(f'assets/webtoon-header.png'), 900).save(f'outputs/Tapas-0.png', "PNG")

	# CTA (call to action) - picked randomly
	CTADir = f'assets/cta'
	randomImageChoice = random.choice([x for x in os.listdir(CTADir) if os.path.isfile(os.path.join(CTADir, x)) and x.endswith('.png')])
	CTAImage = Image.open(f'{CTADir}/{randomImageChoice}')
	createComic([CTAImage], padding, "Random-CTA", comicWidth=1080, comicHeight=1080, rows=1, cols=1, watermark=False)

	# Vertical and Horizontal
	createComic(rawComicPanels, padding, "Vertical", comicWidth=1080+padding*2, comicHeight=1080*numPanels+padding*(numPanels+1), rows=numPanels, cols=1, watermark=True)
	createComic(rawComicPanels, padding, "Horizontal", comicWidth=1080*numPanels+padding*(numPanels+1), comicHeight=1080+padding*2, rows=1, cols=numPanels, watermark=True)

	# Squares
	if numPanels == 2:
		createComic(rawComicPanels, padding, "Square", comicWidth=1080, comicHeight=1080, rows=1, cols=2, watermark=True)
	elif numPanels == 3 or numPanels == 4:
		createComic(rawComicPanels, padding, "Square", comicWidth=1080, comicHeight=1080, rows=2, cols=2, watermark=True)
	elif numPanels == 5 or numPanels == 6:
		createComic(rawComicPanels, padding, "Square", comicWidth=1080, comicHeight=1080, rows=3, cols=2, watermark=True)
	elif numPanels == 8 or numPanels == 9:
		createComic(rawComicPanels, padding, "3x3-Square", comicWidth=1080, comicHeight=1080, rows=3, cols=3, watermark=True)

	# Patreon Comics
	if numPanels == 2:
		createComic(rawComicPanels, padding, "Patreon-1", comicWidth=1080*numPanels+padding*(numPanels+1), comicHeight=1080+padding*2, rows=1, cols=numPanels, watermark=True)
		createComic(lineartOnlyPanels, padding, "Patreon-2", comicWidth=1080*numPanels+padding*(numPanels+1), comicHeight=1080+padding*2, rows=1, cols=numPanels, watermark=True)
		createComic(noTextNoBubblePanels, padding, "Patreon-3", comicWidth=1080*numPanels+padding*(numPanels+1), comicHeight=1080+padding*2, rows=1, cols=numPanels, watermark=True)
		createComic(noTextPanels, padding, "Patreon-4", comicWidth=1080*numPanels+padding*(numPanels+1), comicHeight=1080+padding*2, rows=1, cols=numPanels, watermark=True)
	elif numPanels == 3 or numPanels == 4:
		createComic(sketchOnlyPanels, padding, "Patreon-1", comicWidth=1080, comicHeight=1080, rows=2, cols=2, watermark=True)
		createComic(lineartOnlyPanels, padding, "Patreon-2", comicWidth=1080, comicHeight=1080, rows=2, cols=2, watermark=True)
		createComic(noTextNoBubblePanels, padding, "Patreon-3", comicWidth=1080, comicHeight=1080, rows=2, cols=2, watermark=True)
		createComic(noTextPanels, padding, "Patreon-4", comicWidth=1080, comicHeight=1080, rows=2, cols=2, watermark=True)

	# VIDEO SLICER
	createYouTubeThumbnail(noTextNoBubblePanels[0], titleText)

	panelsImage = Image.new("RGBA", psdImage.size)
	charactersImage = Image.new("RGBA", psdImage.size)
	bubblesImage = Image.new("RGBA", psdImage.size)
	layerEffectsImage = Image.new("RGBA", psdImage.size)

	for i, layerImage in enumerate(layerImages):
		if "Text" in layerNames[i] or "BubbleOutline" in layerNames[i] or "BubbleColor" in layerNames[i]:
			bubblesImage = Image.alpha_composite(bubblesImage, layerImage)


		if "Outline" in layerNames[i] or "Color" in layerNames[i]:
			if "Bubble" not in layerNames[i]:
				charactersImage = Image.alpha_composite(charactersImage, layerImage)

		if "Layer" in layerNames[i]:
			layerEffectsImage = Image.alpha_composite(layerEffectsImage, layerImage)

		if "Panel" in layerNames[i]:
			panelsImage = Image.alpha_composite(panelsImage, layerImage)

	panelsPanels = getPanels(panelsImage, panelWidth)
	charactersPanels = getPanels(charactersImage, panelWidth)
	bubblesPanels = getPanels(bubblesImage, panelWidth)
	layerEffectsPanels = getPanels(layerEffectsImage, panelWidth)

	bbox = []
	for i in range(numPanels):
		panelsPanels[i].save(f'outputs/Panel-{i + 1}.png', "PNG")
		charactersPanels[i ].save(f'outputs/Panel-{i + 1}-Character.png', "PNG")
		bubblesPanels[i].save(f'outputs/Panel-{i + 1}-Text.png', "PNG")
		layerEffectsPanels[i].save(f'outputs/Panel-{i + 1}-Effects.png', "PNG")


def main():
	titleTextList = sys.argv[1]
	shutil.rmtree("outputs/")

	PostingHelper.openTabs()

	inputfiles = []
	for dirpath, dirnames, filenames in os.walk('./inputs'):
		for f in filenames:
			inputfiles.append(os.path.join(dirpath, f))

	for i, inputfile in enumerate(inputfiles):
		ComicSlicer(inputfile, titleTextList[i].upper())

main()