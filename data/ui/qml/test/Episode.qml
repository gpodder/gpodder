
import Qt 4.7

QtObject {
    id: that
    property variant modelData: that

    /* begin: */
    property string qtitle: 'Episode title'
    property string qdescription: 'This is an <strong>example</strong> episode'
    property string qsourceurl: 'http://media.libsyn.com/media/linuxoutlaws/linuxoutlaws190.mp3'
    property string qfiletype: 'audio'
    property string qpositiontext: ''+qposition+' / ' + qduration
    property int qposition: 0
    property int qduration: 0
    property bool qnew: true
    property bool qdownloading: false
    property real qprogress: .4
    /* :end */
}

