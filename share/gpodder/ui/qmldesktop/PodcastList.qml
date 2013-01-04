import QtQuick 1.1
import QtDesktop 0.1
import 'config.js' as Config

Item {
  id: podcastList
  height: childrenRect.height

  property alias model: listView.model
  property alias moving: listView.moving
  property bool hasItems: listView.visible

  signal podcastSelected(variant podcast)
  signal podcastContextMenu(variant podcast)
  signal subscribe

  Text {
    id: addFirstPodcast
    color: '#aaa'
    horizontalAlignment: Text.AlignHCenter
    text: _('No podcasts.') + '\n' + _('Add your first podcast now.')
    visible: !listView.visible
    wrapMode: Text.WordWrap

    MouseArea {
      anchors.fill: parent
      onClicked: podcastList.subscribe()
    }
  }

  Button {
    visible: !listView.visible
    text: _('Add a new podcast')
    onClicked: podcastList.subscribe()
    anchors {
      top: addFirstPodcast.bottom
      left: podcastList.left
      right: podcastList.right
      margins: 70
    }
  }

  ListView {
    id: listView
    visible: count > 1
    anchors{
      left: parent.left
      right: parent.right
    }

    Text {
      id: name
      text: listView.count
    }

    section.property: 'section'
    section.delegate: Item {
      height: Config.headerHeight
      Label {
        font.pixelSize: parent.height * .5
        wrapMode: Text.NoWrap
        text: section
        color: "#aaa"
        anchors {
          leftMargin: Config.iconSize * 1.3 + Config.smallSpacing
//          bottom: parent.bottom
          left: parent.left
          right: parent.right
        }
      }
    }

    delegate: PodcastItem {
      anchors{
        left: parent.left
        right: parent.right
      }
      onSelected: podcastList.podcastSelected(item)
      onContextMenu: podcastList.podcastContextMenu(item)
    }
    //        cacheBuffer: height
  }
}
