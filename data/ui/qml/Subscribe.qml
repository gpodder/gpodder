
import Qt 4.7

Item {
    width: 500
    height: 500

    Item {
        id: topBar
        height: 70

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
        }

        Text {
            id: searchLabel
            text: 'Search for:'
            color: 'white'
            font.pixelSize: 20
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
            }
        }

        TextInput {
            id: searchInput
            color: 'white'
            font.pixelSize: 20
            anchors {
                left: searchLabel.right
                right: searchButton.left
                verticalCenter: parent.verticalCenter
            }
        }

        Rectangle {
            id: searchButton
            anchors {
                top: parent.top
                right: parent.right
            }

            color: 'blue'
            height: parent.height
            width: 100

            Text {
                id: searchButtonLabel
                color: 'white'
                anchors.centerIn: parent
                text: 'Search'
                font.pixelSize: 20
            }

            MouseArea {
                anchors.fill: parent
                onClicked: opmlListModel.searchFor(searchInput.text)
            }
        }
    }

    ListView {
        clip: true

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            top: topBar.bottom
        }

        model: OpmlListModel {
            id: opmlListModel

            function searchFor(query) {
                console.log('Searching for: ' + query)
                source = 'http://gpodder.net/search.opml?q=' + query
                console.log('new source:' + source)
            }
        }

        delegate: SelectableItem {
            property string modelData: url

            height: 50; width: parent.width
            Text {
                text: title
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                color: 'white'
                font.pixelSize: 25
            }
            onSelected: console.log('clicked on: ' + item)
        }
    }

    Rectangle {
        anchors.centerIn: parent

        width: 100
        height: 50

        color: 'black'
        opacity: (opmlListModel.status == XmlListModel.Loading)?1:0

        Behavior on opacity { PropertyAnimation { } }

        Text {
            anchors.centerIn: parent
            text: 'loading...'
            color: 'white'
            font.pixelSize: 14
        }
    }

}

