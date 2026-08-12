# Modified for the XMU theme by 李坤泰 (lktlktlkt1), 2026.
# latexmk configuration for the plain (Madrid-based) academic deck.
# Build with XeLaTeX and make the reusable xmu-theme folder importable.
$pdf_mode = 5;            # 5 = xelatex
$xelatex = 'xelatex -interaction=nonstopmode -synctex=1 %O %S';

# Put the bundled reusable theme folder on the search path so \usetheme{xmu}
# (and its color sub-theme + elements) resolve without installing anything.
# Direct $ENV assignment (not ensure_path): ensure_path does not propagate to the
# xdvipdfmx child on Windows, which then fails to find images (e.g. the avatar).
$ENV{'TEXINPUTS'} = './xmu-theme//;' . ($ENV{'TEXINPUTS'} // '');
