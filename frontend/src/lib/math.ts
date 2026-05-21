import katex from "katex";

/** Render `text` with inline KaTeX. `$...$` delimits inline math, `$$...$$` blocks. */
export function renderMath(text: string): string {
  if (!text) return "";
  // Block first so $...$ inside doesn't match the boundaries.
  let out = text.replace(/\$\$([^$]+)\$\$/g, (_, expr) => {
    try {
      return katex.renderToString(expr, { displayMode: true, throwOnError: false });
    } catch {
      return expr;
    }
  });
  out = out.replace(/\$([^$\n]+)\$/g, (_, expr) => {
    try {
      return katex.renderToString(expr, { displayMode: false, throwOnError: false });
    } catch {
      return expr;
    }
  });
  return out;
}
