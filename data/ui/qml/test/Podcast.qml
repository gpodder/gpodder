
import Qt 4.7

Item {
    id: that
    property variant modelData: that
    function qupdate() { /* ... */ }

    /* begin: */
    property bool qupdating: false
    property string qtitle: 'A Podcast'
    property string qcoverfile: 'test/folder.jpg'
    property int qdownloaded: 3
    property int qnew: 0
    property string qdescription: 'This is a podcast'
    property string qsection: 'audio'
    /* :end */
}

