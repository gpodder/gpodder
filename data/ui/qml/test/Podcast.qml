
import Qt 4.7

Item {
    id: that
    property variant modelData: that

    function qupdate() { /* ... */ }
    property bool qupdating: false
    property string qtitle: 'A Podcast'
    property string qcoverfile: 'test/folder.jpg'
    property int qdownloaded: 3 /* FIXME */
    property string qdescription: 'This is a podcast'
    property string qsection: 'audio' /* FIXME */
}

