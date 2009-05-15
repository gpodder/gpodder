%module gtkbuilderi18n

%{
#include <libintl.h>
%}

extern char* bindtextdomain(char* domain, char* localedir=NULL);

