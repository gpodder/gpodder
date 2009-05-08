<?xml version="1.0"?>
<!--
  Clean-up GtkBuilder UI Interface Description (after conversion from Glade)
  Thomas Perl <thpinfo.com>, 2009-05-08

  Usage: xsltproc gtk-builder-clean.xslt <interfacefile.ui>
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <!-- Remove the last modification timestamps -->
    <xsl:template match="@last_modification_time"/>

    <!-- Make a verbatim copy of the rest of the XML file -->
    <xsl:template match="node()|@*">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()" />
        </xsl:copy>
    </xsl:template>
</xsl:stylesheet>

