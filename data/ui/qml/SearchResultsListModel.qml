
import Qt 4.7

/**
 * XmlListModel exposing the podcasts in an OPML file:
 * - title
 * - description
 * - url
 **/

XmlListModel {
    query: '//podcast'

    XmlRole { name: 'title'; query: 'title/string()' }
    XmlRole { name: 'description'; query: 'description/string()' }
    XmlRole { name: 'url'; query: 'url/string()' }
    XmlRole { name: 'subscribers'; query: 'subscribers/string()' }
    XmlRole { name: 'logo'; query: 'scaled_logo_url/string()' }
}

