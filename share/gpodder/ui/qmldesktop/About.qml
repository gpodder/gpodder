import QtQuick 1.1
import QtDesktop 0.1
import "config.js" as Config

Window {
  id: about
  width: 400
  height: 300

  Image {
    id: image1
    anchors.top: parent.top
    anchors.left: parent.left
    anchors.margins: Config.smallSpacing
    width: 50
    height: 50
    fillMode: Image.PreserveAspectFit
    smooth: true
    source: Config.artworkDir + 'gpodder200.png'
  }

  Label {
    id: appName
    text: "<b><big>gPodder</big> %s</b>"
    anchors.left: image1.right
    anchors.margins: Config.smallSpacing
  }

  Label {
    id: url
    text: '<small><a href="'+ controller.getURL() +'">' + controller.getURL() + '</a></small>'
    anchors.top: appName.bottom
    anchors.left: image1.right
    anchors.margins: Config.smallSpacing
    onLinkActivated: Qt.openUrlExternally(link)
  }

  Rectangle {
    id: separator
    color: "silver"
    height: 1
    anchors.top: image1.bottom
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.margins: Config.smallSpacing
  }

  Label {
    id: copyright
    text: controller.getCopyright()
    horizontalAlignment: Text.AlignHCenter
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: separator.bottom
    anchors.margins: Config.smallSpacing
  }

  Item {
    id: buttons
    height: childrenRect.height
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: copyright.bottom
    anchors.margins: Config.smallSpacing

    Button {
      id: btnSupport
      text: _("Donate / Wishlist")
      anchors.left: parent.left
      onClicked: Qt.openUrlExternally('http://gpodder.org/donate')
    }

    Button {
      id: btnBugTracker
      text: _("Report a problem")
      anchors.right: parent.right
      onClicked: Qt.openUrlExternally(Config.bugTrackerURL)
    }
  }

  ScrollArea{
    id: creditsArea
    anchors.top: buttons.bottom
    anchors.right: parent.right
    anchors.bottom: btnClose.top
    anchors.left: parent.left
    anchors.margins: Config.smallSpacing

    TextEdit {
      text: controller.getCredits()
      anchors.top: parent.top
      anchors.left: parent.left
      readOnly: true
    }
  }

  Button {
    id: btnClose
    text: _("Close")
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.margins: Config.smallSpacing

    onClicked: about.close()
  }
}
