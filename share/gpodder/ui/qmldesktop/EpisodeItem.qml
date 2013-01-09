import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

SelectableItem {
//  Item{
  id: episodeItem

  // Show context menu when single-touching the icon
//  singlePressContextMenuLeftBorder: title.x
  onSelected2: episodeList.currentIndex = index

  Rectangle {
    id: downloadProgress
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    width: parent.width * modelData.qprogress
    height: modelData.qdownloading?parent.height:0
    color: Config.downloadColor
    opacity: modelData.qdownloaded?0:.3
    Behavior on opacity { PropertyAnimation { } }
    Behavior on height { PropertyAnimation { } }
  }

  Rectangle {
    id: playbackProgress

    anchors.left: parent.left

    anchors.verticalCenter: parent.verticalCenter
    width: modelData.qduration?(parent.width * (modelData.qposition / modelData.qduration)):0
    height: parent.height
    color: Config.playbackColor
    opacity: .3
  }

  Image {
    id: icon
    source: {
      if (episodeModel.is_subset_view) {
        Util.formatCoverURL(modelData.qpodcast)
      } else {
        Config.artworkDir + modelData.qfiletype + (modelData.qdownloading?'-downloading':(modelData.qplaying?'-playing':'')) + '.png'
      }
    }
    sourceSize.width: width
    sourceSize.height: height

    width: Config.iconSize
    height: Config.iconSize
    anchors {
      verticalCenter: parent.verticalCenter
      left: parent.left
      leftMargin: Config.smallSpacing
    }
    opacity: (modelData.qdownloaded || modelData.qdownloading)?1:.3
    Behavior on opacity { PropertyAnimation { } }
  }

  Label {
    id: title
    text: modelData.qtitle
    font.bold: true
    anchors {
      left: icon.right
      bottom: parent.verticalCenter
      right: fileSize.left
      leftMargin: Config.smallSpacing
      rightMargin: Config.smallSpacing
    }
    clip: true
  }

  Label {
    id: fileSize
    text: modelData.qfilesize
    anchors {
      right: positionInfo.left
      rightMargin: Config.smallSpacing
      verticalCenter: parent.verticalCenter
    }
  }

  Label {
    id: positionInfo
    text: modelData.qduration ? Util.formatDuration(modelData.qduration) : ''
    anchors {
      right: pubDate.left
      rightMargin: Config.smallSpacing
      verticalCenter: parent.verticalCenter
    }
  }

  Label {
    id: pubDate
    text: modelData.qpubdate
    anchors {
      right: archiveIcon.visible ? archiveIcon.left : parent.right
      rightMargin: Config.largeSpacing
      verticalCenter: parent.verticalCenter
    }
  }

  Image {
    id: archiveIcon
    source: Config.artworkDir + 'episode-archive.png'
    opacity: .5
    visible: modelData.qarchive
    width: Config.iconSize
    height: Config.iconSize
    anchors {
      right: parent.right
      verticalCenter: parent.verticalCenter
      rightMargin: Config.largeSpacing
    }
  }
}
