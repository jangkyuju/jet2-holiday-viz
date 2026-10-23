// Inlines the data scripts into the page and writes the site.
// Usage: node src/build.mjs src/index.src.html <artifact-out.html> index.html src/map-data.js src/site-data.js
import fs from 'fs';
const [src, outFrag, outFull, ...dataFiles] = process.argv.slice(2);
const data = dataFiles.map(f => fs.readFileSync(f, 'utf8')).join('\n');
const frag = fs.readFileSync(src, 'utf8').replace('/*MAPDATA*/', () => data);
fs.writeFileSync(outFrag, frag);
fs.writeFileSync(outFull, `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n${frag}\n</body>\n</html>\n`);
