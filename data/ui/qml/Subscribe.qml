
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
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
            }
        }

        TextInput {
            id: searchInput
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
            }

            MouseArea {
                anchors.fill: parent
                onClicked: opmlListModel.searchFor(searchInput.text)
            }
        }
    }

    ListView {
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

        delegate: Text {
            text: title + '\n' + description; height: 50; width: 200
            MouseArea {
                anchors.fill: parent
                onClicked: console.log('clicked on: ' + url)
            }
        }
    }

    Rectangle {
        width: 100
        height: 100
        color: 'red'
        opacity: (opmlListModel.status == XmlListModel.Loading)?1:0

        Text {
            anchors.fill: parent
            text: 'please wait..'
            color: 'white'
        }

        Rectangle {
            width: parent.width*opmlListModel.progress
            height: parent.height
        }
    }

}

