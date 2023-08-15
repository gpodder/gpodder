<?xml version="1.0" ?>
<!-- this stylesheet adjusts menu item accelerators:
     - Command-, for preferences
     - Command-? for user manual

     accelerators names are found in gtk/source/gtk+/gdk/gdkkeysyms-compat.h
  -->
<xsl:stylesheet
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	version="1.0">

	<xsl:template match="@*|node()">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
	</xsl:template>

	<xsl:template match="attribute[@name = 'accel' and preceding-sibling::attribute[@name = 'action' and . = 'app.preferences']]">
		<attribute name="accel">&lt;Primary&gt;,</attribute>
	</xsl:template>

	<xsl:template match="attribute[@name='action' and . ='app.help']">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()"/>
		</xsl:copy>
		<attribute name="accel">&lt;Primary&gt;?</attribute>
	</xsl:template>

</xsl:stylesheet>

