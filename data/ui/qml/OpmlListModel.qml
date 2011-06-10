
import Qt 4.7

/**
 * XmlListModel exposing the podcasts in an OPML file:
 * - title
 * - description
 * - url
 **/

XmlListModel {
    query: '/opml/body/outline'

    XmlRole { name: 'title'; query: '@title/string()' }
    XmlRole { name: 'description'; query: '@text/string()' }
    XmlRole { name: 'url'; query: '@xmlUrl/string()' }
}

