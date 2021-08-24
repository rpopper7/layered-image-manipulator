# Layered-Image-Manipulator

The Layered Image Manipulator is a python script / tool that can help format multi-layer PSD images into PNG images that are perfect to post on social media. It can do the following: 

* resize images to recommended social media size
* convert multiple images into a correctly sized comic / collage image
* stamp images with watermarks 
* add borders to images
* create thumbnails of images for YouTube
* splice out the sketch, outline, and text layers and create new images from them
* open social media links in the web browser to prepare for posting

## Technologies

* Pillow : a friendly PIL fork for the Python Imaging Library for image processing
* psd-tools : a Python package for working with layered Adobe Photoshop PSD files

## How to Run

1. Set up an assets folder of the required .PNG image assets (watermark, signature, call to action images)
2. Put a .PNG image in the inputs folder
3. Run LayeredImageManipulator.py and put in the required argument for title


## Future Improvements - Coming Soon

* customize which Social Media formats you want & do not want
* more formats for comics
* customize some text