import io
import zipfile

buf = io.BytesIO()
z = zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED)
z.writestr('mimetype', 'application/epub+zip')

container = '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
z.writestr('META-INF/container.xml', container)

opf = '''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0" unique-identifier="bookid">
  <metadata>
    <dc:title>Test Book</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">urn:test:001</dc:identifier>
    <dc:description>A test book.</dc:description>
    <dc:publisher>Test Publisher</dc:publisher>
    <dc:date>2024-01-01</dc:date>
    <dc:rights>Public Domain</dc:rights>
    <dc:subject>Fiction</dc:subject>
    <meta name="cover" content="cover-img"/>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ncx"/>
  </spine>
</package>'''
z.writestr('OEBPS/content.opf', opf)

toc = '''<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <head><meta name="dtb:uid" content="test"/></head>
  <docTitle><text>Test</text></docTitle>
  <navMap><navPoint id="nav1"><navLabel><text>Chapter 1</text></navLabel><content src="ch1.xhtml"/></navPoint></navMap>
</ncx>'''
z.writestr('OEBPS/toc.ncx', toc)
z.close()

with open('test.epub', 'wb') as f:
    f.write(buf.getvalue())
print('test.epub created')
