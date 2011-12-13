
import Qt 4.7

import com.nokia.meego 1.0

import 'config.js' as Config

Item {
    id: podcastList

    property alias model: listView.model
    property alias moving: listView.moving

    signal podcastSelected(variant podcast)
    signal podcastContextMenu(variant podcast)
    signal subscribe

    Text {
        anchors.centerIn: parent
        color: 'white'
        font.pixelSize: 30
        horizontalAlignment: Text.AlignHCenter
        text: '<big>' + _('No podcasts') + '</big><br><small>' + _('Touch here to add a podcast') + '</small>'
        visible: !listView.visible

        MouseArea {
            anchors.fill: parent
            onClicked: podcastList.subscribe()
        }
    }

    ListView {
        id: listView
        anchors.fill: parent
        visible: count > 1

        section.property: 'section'
        section.delegate: Item {
            height: Config.headerHeight
            Label {
                font.pixelSize: parent.height * .5
                wrapMode: Text.NoWrap
                text: section
                color: "#aaa"
                anchors {
                    //bottomMargin: Config.smallSpacing
                    leftMargin: Config.switcherWidth / 3
                    bottom: parent.bottom
                    left: parent.left
                    right: parent.right
                }
            }
        }

        delegate: PodcastItem {
            onSelected: podcastList.podcastSelected(item)
            onContextMenu: podcastList.podcastContextMenu(item)
        }

        header: Item { height: titleBar.height }
        footer: Item { height: Config.headerHeight }

        cacheBuffer: height
    }

    ScrollDecorator {
        flickableItem: listView
    }

}

