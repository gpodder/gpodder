import QtQuick 1.1
import QtDesktop 0.1
import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
  id: podcastItem
  height: 50
  anchors{
    left: parent.left
    right: parent.right
  }

  // Show context menu when single-touching the count or cover art
  singlePressContextMenuLeftBorder: titleBox.x

  Image {
    id: cover
    z:-1

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
    color: (counters.newEpisodes > 0)?Config.newColor:"white"

    anchors {
      verticalCenter: parent.verticalCenter
//      left: cover.visible?cover.right:cover.left
      left: cover.right
      leftMargin: Config.smallSpacing
//      right: parent.right
      rightMargin: Config.smallSpacing
    }
  }

  Item {
    id: spinner
    anchors {
      verticalCenter: parent.verticalCenter
      right: titleBox.left
      rightMargin: Config.smallSpacing
    }
    visible: modelData.qupdating
  }

  Rectangle {
    id: counterBox
    width: Config.iconSize
    height: width
    color: "black"

    anchors {
      right: parent.right
      verticalCenter: parent.verticalCenter
    }

    Label {
      id: counters

      property int newEpisodes: modelData.qnew
      property int downloadedEpisodes: modelData.qdownloaded

      anchors {
        verticalCenter: parent.verticalCenter
        right: parent.right
        rightMargin: 3
      }

      visible: !spinner.visible && (downloadedEpisodes > 0)
      text: counters.downloadedEpisodes
      color: "white"

      font.pixelSize: podcastItem.height * .4
    }
  }
}
