
import QtQuick 1.1

import org.gpodder.qmlui 1.0

import 'config.js' as Config

Rectangle {
    id: showNotes

    clip: true
    property variant episode: undefined

    MouseArea {
        // clicks should not fall through!
        anchors.fill: parent
    }

    Flickable {
        id: showNotesFlickable
        anchors.fill: parent

        contentHeight: showNotesText.height
        anchors.margins: Config.largeSpacing

        Label {
            id: showNotesText
            color: "black"
            font.pixelSize: 20 * Config.scale
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            wrapMode: Text.Wrap
            text: episode!=undefined?('<h3 color="#666">'+episode.qtitle+'</h3><small>'+formatSubtitle()+'</small><p>'+episode.qdescription+'</p>'):'No episode selected'
            onLinkActivated: Qt.openUrlExternally(link)

            function formatSubtitle() {
                var pubdate = episode.qpubdate;
                var filesize = episode.qfilesize;
                var filename = episode.qsourceurl
                if (filesize !== '') {
                    if (episode.qdownloaded) {
                        var filename = episode.qsourceurl.split('/').pop();
                        return pubdate + ' | ' + filesize + ' | ' + filename;
                    }

                    return pubdate + ' | ' + filesize;
                } else {
                    return pubdate;
                }
            }
        }
    }

    ScrollScroll {
        flickable: showNotesFlickable
    }
}

