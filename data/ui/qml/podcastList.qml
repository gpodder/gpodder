
import Qt 4.7

Rectangle {
    id: rectangle
    color: "black"

    ListView {
        anchors.fill: parent
        anchors.bottomMargin: toolbar.height

        delegate: PodcastItem {}
        model: podcastModel
        snapMode: ListView.SnapToItem
    }

    Image {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: toolbar.top
        source: 'podcastList/toolbar_shadow.png'
        opacity: toolbar.opacity
    }

    Toolbar {
        id: toolbar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        opacity: height?1:0

        ToolbarButton { source: 'podcastList/tb_refresh.png'; onClicked: rectangle.color = "red" }
        ToolbarButton { source: 'podcastList/tb_add.png'; onClicked: rectangle.color = "green" }
        ToolbarButton { source: 'podcastList/tb_delete.png'; onClicked: rectangle.color = "blue" }
    }

}

