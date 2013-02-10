import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Window {
  id: item1
  property variant myController: undefined

  width: Config.windowWidth
  height: Config.windowHeight

  Label {
    id: label1
    text: Util._("<big>Welcome to gPodder</big>")
    anchors.top: parent.top
    anchors.left: parent.left
  }

  Label {
    id: label2
    text: Util._("Your podcast list is empty.")
    anchors.left: parent.left
    anchors.top: label1.bottom
  }

  Button {
    id: btnOPML
    text: Util._("Choose from a list of example podcasts")
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: label2.bottom
  }

  Button {
    id: btnAddURL
    text: Util._("Add a podcast by entering its URL")
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: btnOPML.bottom
  }

  Button {
    id: btnMygPodder
    text: Util._("Restore my subscriptions from gpodder.net")
    anchors.top: btnAddURL.bottom
    anchors.right: parent.right
    anchors.left: parent.left
  }

  Button {
    id: btnCancel
    text: Util._("Cancel")
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    onClicked: myController.close()
  }
}
