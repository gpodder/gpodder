
import Qt 4.7

Rectangle {
    id: rectangle
    color: "white"

    Image {
        anchors.fill: parent
        source: 'podcastList/mask.png'
        sourceSize { height: 100; width: 100 }
    }

    Image {
        opacity: 1
        anchors.fill: parent
        source: 'podcastList/noise.png'
    }

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

        ToolbarButton { source: 'podcastList/tb_refresh.png'; onClicked: rectangle.color = "#faa" }
        ToolbarButton { source: 'podcastList/tb_add.png'; onClicked: rectangle.color = "#afa" }
        ToolbarButton { source: 'podcastList/tb_search.png'; onClicked: rectangle.color = "#aaf" }
    }

}

