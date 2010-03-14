#!/bin/bash
cd work/gpodder-2.3

# create temporary directory
mkdir tmpdir

# create raster images for the icons
for i in 32 48 128
do rsvg -w $i -h $i data/gpodder.svg tmpdir/gpodder-$i.png
done

# get the small one
cp data/icons/16/gpodder.png tmpdir/gpodder-16.png

# create the icns file (thanks to the icnsutils library http://icns.sourceforge.net/)
png2icns tmpdir/icon.icns tmpdir/gpodder-{16,32,48,128}.png
