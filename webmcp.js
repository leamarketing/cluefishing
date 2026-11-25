// WebMCP: read-only tools that let an AI agent in the visitor's browser use this site.
// Spec and status: https://developer.chrome.com/docs/ai/webmcp/imperative-api
// The API is in origin trial and may change. Browsers without it skip this file entirely.
(function () {
  if (!('modelContext' in document) || !document.modelContext || typeof document.modelContext.registerTool !== 'function') return;

  var ORIGIN = location.origin;
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  function lang(input) {
    var l = input && typeof input.language === 'string' ? input.language.toLowerCase() : '';
    if (l === 'no' || l === 'nb' || l === 'nn') return 'no';
    if (l === 'en') return 'en';
    return (document.documentElement.lang || 'en').indexOf('no') === 0 ? 'no' : 'en';
  }
  function archiveUrl(l) { return ORIGIN + (l === 'no' ? '/no/news/' : '/news/'); }

  function fetchDoc(url, signal) {
    return fetch(url, { signal: signal, credentials: 'omit' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    }).then(function (html) { return new DOMParser().parseFromString(html, 'text/html'); });
  }

  function listEditions(l, signal) {
    var base = archiveUrl(l);
    return fetchDoc(base, signal).then(function (doc) {
      var out = [];
      doc.querySelectorAll('a[href]').forEach(function (a) {
        var m = (a.getAttribute('href') || '').match(/(\d{4}-\d{2}-\d{2})\.html$/);
        if (m) out.push({ date: m[1], title: a.textContent.trim(), url: new URL(a.getAttribute('href'), base).href });
      });
      return out;
    });
  }

  function readEdition(url, signal) {
    return fetchDoc(url, signal).then(function (doc) {
      var stories = [];
      doc.querySelectorAll('.news-item').forEach(function (item) {
        var h = item.querySelector('h3');
        var p = item.querySelector('p');
        var src = item.querySelector('a.source');
        if (!h) return;
        stories.push({
          headline: h.textContent.trim(),
          summary: p ? p.textContent.trim() : '',
          source_url: src ? src.href : null
        });
      });
      var h1 = doc.querySelector('h1');
      return { url: url, edition: h1 ? h1.textContent.trim() : '', stories: stories };
    });
  }

  function safe(fn) {
    return function (input, ctx) {
      var signal = ctx && ctx.signal;
      return Promise.resolve().then(function () { return fn(input || {}, signal); }).catch(function (e) {
        return { error: String(e && e.message ? e.message : e) };
      });
    };
  }

  var langSchema = { type: 'string', enum: ['en', 'no'], description: 'Page language: "en" for English, "no" for Norwegian. Defaults to the current page language.' };

  var tools = [
    {
      name: 'list_ai_news_editions',
      description: 'List every Cluefishing AI News edition (newest first) with its date and URL. Editions summarise real, sourced AI developments, with a focus on disclosure and labelling of AI content.',
      inputSchema: { type: 'object', properties: { language: langSchema } },
      annotations: { readOnlyHint: true },
      execute: safe(function (input, signal) {
        var l = lang(input);
        return listEditions(l, signal).then(function (eds) { return { language: l, editions: eds }; });
      })
    },
    {
      name: 'get_ai_news_edition',
      description: 'Get the stories in one Cluefishing AI News edition: headline, short summary and the original source link for each story. Leave out the date to get the newest edition.',
      inputSchema: {
        type: 'object',
        properties: {
          date: { type: 'string', pattern: '^\\d{4}-\\d{2}-\\d{2}$', description: 'Edition date as YYYY-MM-DD. Optional.' },
          language: langSchema
        }
      },
      annotations: { readOnlyHint: true },
      execute: safe(function (input, signal) {
        var l = lang(input);
        var date = typeof input.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(input.date) ? input.date : null;
        return listEditions(l, signal).then(function (eds) {
          if (!eds.length) return { error: 'No editions found.' };
          var hit = date ? eds.filter(function (e) { return e.date === date; })[0] : eds[0];
          if (!hit) {
            var d = date.split('-');
            return { error: 'No edition for ' + Number(d[2]) + ' ' + MONTHS[Number(d[1]) - 1] + ' ' + d[0] + '.', available_dates: eds.map(function (e) { return e.date; }) };
          }
          return readEdition(hit.url, signal).then(function (ed) { ed.date = hit.date; ed.language = l; return ed; });
        });
      })
    },
    {
      name: 'get_disclosure_checklist',
      description: 'Get the Cluefishing disclosure checklist: six questions to run your own work through before publishing, so readers know where AI was used.',
      inputSchema: { type: 'object', properties: { language: langSchema } },
      annotations: { readOnlyHint: true },
      execute: safe(function (input, signal) {
        var l = lang(input);
        var url = ORIGIN + (l === 'no' ? '/no/' : '/');
        return fetch(url, { signal: signal, credentials: 'omit' }).then(function (r) { return r.text(); }).then(function (html) {
          var items = [];
          var re = /\{id:"c\d+",\s*code:"(\d+)",\s*label:"((?:[^"\\]|\\.)*)"\}/g, m;
          while ((m = re.exec(html))) items.push({ number: m[1], question: m[2].replace(/\\"/g, '"') });
          if (!items.length) return { error: 'Checklist not found on ' + url };
          return { language: l, page: url + '#tacklebox', items: items };
        });
      })
    },
    {
      name: 'get_site_info',
      description: 'Who runs Cluefishing, how AI is used to make the site, how to contact it, and its privacy notice.',
      inputSchema: { type: 'object', properties: { language: langSchema } },
      annotations: { readOnlyHint: true },
      execute: safe(function (input) {
        var l = lang(input);
        return {
          site: 'Cluefishing',
          about_page: ORIGIN + (l === 'no' ? '/no/om.html' : '/about.html'),
          responsible: 'Geir Amdal, Nordreisa, Norway',
          contact: 'https://github.com/leamarketing/cluefishing/issues',
          ai_use: 'AI News editions are researched and drafted by an AI assistant (Claude) from linked sources and approved by Geir Amdal before they go live. Story pictures are generated with an AI image tool, then cropped.',
          tracking: 'No analytics, no cookies, no advertising.'
        };
      })
    }
  ];

  tools.forEach(function (t) {
    try {
      var p = document.modelContext.registerTool(t);
      if (p && typeof p.catch === 'function') p.catch(function () {});
    } catch (e) { /* the API is experimental: never break the page */ }
  });
})();
