
import Qt 4.7

import com.nokia.meego 1.0

import 'config.js' as Config

Rectangle {
    id: showNotes

    clip: true
    property variant episode: undefined
    radius: 10

    MouseArea {
        // clicks should not fall through!
        anchors.fill: parent
    }

    Flickable {
        id: showNotesFlickable
        anchors.fill: parent

        contentHeight: showNotesText.height
        anchors.margins: Config.largeSpacing

        Text {
            id: showNotesText
            color: "black"
            font.pixelSize: 20 * Config.scale
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            wrapMode: Text.Wrap
            text: episode!=undefined?('<h3 color="#666">'+episode.qtitle+'</h3>\n\n'+episode.qdescription):'No episode selected'
        }
    }

    ScrollDecorator {
        flickableItem: showNotesFlickable
    }
}

