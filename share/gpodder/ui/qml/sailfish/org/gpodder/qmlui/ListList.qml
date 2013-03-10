
import Sailfish.Silica 1.0
import QtQuick 1.1

SilicaListView {
    id: listView

    property string headerText: ''
    property int headerHeight: 90

    property bool hasRefresh: false // Unused here, see Harmattan UI
    signal refresh

    header: Item {
        id: listViewHeader
        height: listView.headerHeight
        width: parent.width

        Text {
            anchors {
                verticalCenter: parent.verticalCenter
                right: parent.right
                margins: 20
            }
            text: listView.headerText
            font.pixelSize: 30
            color: "white"
        }
    }
}

