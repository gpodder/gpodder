import QtQuick 1.1
import QtDesktop 0.1
import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
  id: podcastItem

  onSelected: podcastList.podcastSelected(item)
  onSelected2: podcastList.currentIndex = index
  onContextMenu: podcastList.podcastContextMenu(item)

  // Show context menu when single-touching the count or cover art
  singlePressContextMenuLeftBorder: titleBox.x

  Image {
    id: cover

    source: Util.formatCoverURL(modelData)
    asynchronous: true
    width: podcastItem.height * .8
    height: width
    sourceSize.width: width
    sourceSize.height: height

    anchors {
      verticalCenter: parent.verticalCenter
      left: parent.left
      leftMargin: Config.smallSpacing
    }
  }

  Label {
    id: titleBox
    text: modelData.qtitle
    font.bold: true
    clip: true

    anchors {
      bottom: parent.verticalCenter
      left: cover.visible?cover.right:cover.left
      leftMargin: Config.smallSpacing
      right: counters.left
      rightMargin: Config.smallSpacing
    }
  }

  Label {
    id: descriptionBox
    text: modelData.qdescription
    clip: true

    anchors {
      top: titleBox.bottom
      left: titleBox.left
      leftMargin: Config.smallSpacing
      right: counters.left
      rightMargin: Config.smallSpacing
    }
  }

  TextPill {
    id: counters
    property int newEpisodes: modelData.qnew
    property int downloadedEpisodes: modelData.qdownloaded
    z: -1

    visible: downloadedEpisodes > 0
    radius: 5
    leftText: newEpisodes
    rightText: downloadedEpisodes
    width: 40
    height: width / 2

    anchors {
      right: parent.right
      verticalCenter: parent.verticalCenter
    }
  }
}
