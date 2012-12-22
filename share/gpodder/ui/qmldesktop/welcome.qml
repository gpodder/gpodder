import QtQuick 1.1
import QtDesktop 0.1

Window {
  id: item1
  width: 400
  height: 300

  Label {
    id: label1
    text: qsTr("<big>Welcome to gPodder</big>")
    anchors.top: parent.top
    anchors.left: parent.left
  }

  Label {
    id: label2
    text: qsTr("Your podcast list is empty.")
    anchors.left: parent.left
    anchors.top: label1.bottom
  }

  Button {
    id: btnOPML
    text: "Choose from a list of example podcasts"
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: label2.bottom
  }

  Button {
    id: btnAddURL
    text: "Add a podcast by entering its URL"
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: btnOPML.bottom
  }

  Button {
    id: btnMygPodder
    text: "Restore my subscriptions from gpodder.net"
    anchors.top: btnAddURL.bottom
    anchors.right: parent.right
    anchors.left: parent.left
  }

  Button {
    id: btnCancel
    text: "Cancel"
    anchors.right: parent.right
    anchors.bottom: parent.bottom
  }
}
