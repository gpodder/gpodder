# gpodder translation makefile

default:
	for langfile in *.po; do echo $${langfile}; msgmerge -U $${langfile} ../messages.pot; mkdir -p ../locale/`basename $${langfile} .po`/LC_MESSAGES/; msgfmt $${langfile} -o ../locale/`basename $${langfile} .po`/LC_MESSAGES/gpodder.mo; done

clean:
	rm -rf ../locale *~

.PHONY: default clean

