/**
 * Проверка анкоров и индексации в Google Таблице.
 * 1) Заходит по ссылке из столбца 1, проверяет: анкор из столбца 3 и ссылка из столбца 2.
 *    Found: если совпало — «Found» (зелёный), иначе «noFound» (красный).
 * 2) Проверяет индексацию страницы из столбца 1 (site:домен/путь).
 *    Index: если в индексе — «index» (зелёный), иначе «noindex» (красный).
 * Колонки: Page URL | Target URL | Exact Anchor | Found | Index
 */

var COL_PAGE_URL = 'Page URL';
var COL_TARGET_URL = 'Target URL';
var COL_EXACT_ANCHOR = 'Exact Anchor';
var COL_FOUND = 'Found';
var COL_INDEX = 'Index';
var PAUSE_MS = 1000;
var PAUSE_GOOGLE_MS = 2000; // пауза перед запросом к Google, чтобы снизить риск блокировки

function onOpen() {
  try {
    SpreadsheetApp.getUi()
      .createMenu('Анкоры')
      .addItem('Проверить анкоры', 'checkAnchors')
      .addItem('Включить автопроверку раз в день', 'createDailyTrigger')
      .addItem('Отключить автопроверку', 'deleteTriggers')
      .addToUi();
  } catch (e) {}
}

/**
 * Создаёт триггер: раз в день (в 9:00 по времени таблицы) запускается checkAnchors.
 * Новые строки в таблице будут проверяться автоматически.
 * Вызови один раз из меню «Анкоры → Включить автопроверку раз в день».
 */
function createDailyTrigger() {
  deleteTriggers();
  ScriptApp.newTrigger('checkAnchors')
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();
  try {
    SpreadsheetApp.getUi().alert('Автопроверка включена: каждый день в 9:00.');
  } catch (e) {}
}

/**
 * Удаляет все триггеры, связанные с этим скриптом (отключает автопроверку).
 */
function deleteTriggers() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'checkAnchors') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

/**
 * Вызов по URL (веб-приложение). Ассистент открывает этот URL — скрипт проверяет таблицу и заполняет Found.
 * Без Cloud Console: разверни скрипт как веб-приложение и передай URL ассистенту.
 */
function doGet() {
  var count = checkAnchors();
  return ContentService.createTextOutput(JSON.stringify({ ok: true, checked: count }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Проверяет строки таблицы и записывает результат в колонку Found. Возвращает число проверенных строк.
 */
function checkAnchors() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    try { SpreadsheetApp.getUi().alert('Нужна минимум одна строка данных под заголовком.'); } catch (e) {}
    return 0;
  }

  var lastCol = Math.max(sheet.getLastColumn(), 4);
  var data = sheet.getRange(1, 1, lastRow, lastCol).getValues();
  var headers = data[0];
  var colPage = headers.indexOf(COL_PAGE_URL);
  var colTarget = headers.indexOf(COL_TARGET_URL);
  var colAnchor = headers.indexOf(COL_EXACT_ANCHOR);
  var colFound = headers.indexOf(COL_FOUND);

  if (colPage < 0 || colTarget < 0 || colAnchor < 0) {
    try { SpreadsheetApp.getUi().alert('Нужны колонки: Page URL, Target URL, Exact Anchor.'); } catch (e) {}
    return 0;
  }
  if (colFound < 0) {
    colFound = headers.length;
    sheet.getRange(1, colFound + 1).setValue(COL_FOUND);
  }
  var colIndex = headers.indexOf(COL_INDEX);
  if (colIndex < 0) {
    colIndex = colFound + 1;
    sheet.getRange(1, colIndex + 1).setValue(COL_INDEX);
  }

  var numDataRows = lastRow - 1;
  var results = [];
  var resultsIndex = [];
  for (var i = 1; i <= lastRow - 1; i++) {
    var foundVal = 'Error';
    var indexVal = 'Error';
    try {
      var row = data[i] || [];
      var pageUrl = (row[colPage] !== undefined && row[colPage] !== null) ? String(row[colPage]).trim() : '';
      var targetUrl = (row[colTarget] !== undefined && row[colTarget] !== null) ? String(row[colTarget]).trim() : '';
      var exactAnchor = (row[colAnchor] !== undefined && row[colAnchor] !== null) ? String(row[colAnchor]).trim() : '';
      if (pageUrl && targetUrl) {
        var check = fetchAndCheck(pageUrl, targetUrl, exactAnchor);
        foundVal = (check === 'Yes') ? 'Found' : (check === 'No') ? 'noFound' : 'Error';
      }
      if (pageUrl) {
        Utilities.sleep(PAUSE_GOOGLE_MS);
        var idx = checkIndexedInGoogle(pageUrl);
        indexVal = (idx === 'Yes') ? 'index' : (idx === 'No') ? 'noindex' : 'Error';
      }
    } catch (e) {}
    results.push([foundVal]);
    resultsIndex.push([indexVal]);
    if (i < lastRow - 1) {
      Utilities.sleep(PAUSE_MS);
    }
  }

  if (results.length !== numDataRows) {
    try { SpreadsheetApp.getUi().alert('Ошибка: строк результатов ' + results.length + ', ожидалось ' + numDataRows); } catch (err) {}
    return 0;
  }
  var n = results.length;
  if (n > 0) {
    // Диапазон: ровно n строк, 1 колонка (getRange: строка, колонка, число_строк, число_колонок)
    var endRow = 1 + n;
    sheet.getRange(2, colFound + 1, endRow, colFound + 1).setValues(results);
    sheet.getRange(2, colIndex + 1, endRow, colIndex + 1).setValues(resultsIndex);
    var green = '#34a853';
    var red = '#ea4335';
    var gray = '#cccccc';
    var colorsFound = [];
    var colorsIndex = [];
    for (var j = 0; j < n; j++) {
      colorsFound.push([results[j][0] === 'Found' ? green : (results[j][0] === 'noFound' ? red : gray)]);
      colorsIndex.push([resultsIndex[j][0] === 'index' ? green : (resultsIndex[j][0] === 'noindex' ? red : gray)]);
    }
    sheet.getRange(2, colFound + 1, endRow, colFound + 1).setBackgrounds(colorsFound);
    sheet.getRange(2, colIndex + 1, endRow, colIndex + 1).setBackgrounds(colorsIndex);
  }
  try { SpreadsheetApp.getUi().alert('Готово. Проверено строк: ' + results.length + ' (Found + Index).'); } catch (e) {}
  return results.length;
}

/**
 * Проверка индексации — так же, как при ручной проверке, только автоматически.
 * 1) Кэш Google (cache:URL) — как открыть в браузере и посмотреть «в кэше / нет».
 * 2) Выдача site:URL в Google, при необходимости Bing.
 */
function checkIndexedInGoogle(pageUrl) {
  var u = (pageUrl && pageUrl.trim) ? pageUrl.trim() : '';
  if (!u) return 'Error';
  var sitePart = u.replace(/^https?:\/\//i, '').split('#')[0].trim();
  if (!sitePart) return 'Error';
  var query = 'site:' + sitePart;

  // Как вручную: сначала смотрим кэш (cache:URL в поиске или прямой запрос к кэшу)
  var cacheResult = tryGoogleCache(u);
  if (cacheResult === 'Yes') return 'Yes';
  if (cacheResult === 'No') {
    // Кэша нет — проверяем выдачу site:, как при ручном поиске
    var result = tryGoogleSiteSearch(query, u, sitePart);
    if (result === 'Yes') return 'Yes';
    if (result === 'No') return 'No';
    result = tryBingSiteSearch(query, u, sitePart);
    return result;
  }
  return 'Error';
}

/**
 * Проверка по кэшу Google — как при ручной проверке «cache:URL».
 * «В индексе» только если в ответе явно указано, что это кэш нашей страницы (как в браузере).
 */
function tryGoogleCache(pageUrl) {
  var normalizedForMatch = pageUrl.replace(/^https?:\/\//i, '').split('#')[0].split('?')[0].replace(/\/$/, '');
  var variants = [pageUrl, 'https://' + normalizedForMatch, 'http://' + normalizedForMatch];
  for (var v = 0; v < variants.length; v++) {
    var result = tryGoogleCacheOne(variants[v], normalizedForMatch);
    if (result !== 'No') return result;
    if (v < variants.length - 1) Utilities.sleep(800);
  }
  return 'No';
}

function tryGoogleCacheOne(pageUrl, normalizedForMatch) {
  try {
    var cacheUrl = 'https://webcache.googleusercontent.com/search?q=cache:' + encodeURIComponent(pageUrl);
    var response = UrlFetchApp.fetch(cacheUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/'
      }
    });
    var code = response.getResponseCode();
    if (code !== 200) return 'No';
    var html = response.getContentText();
    if (!html || html.length < 300) return 'No';
    var htmlLower = html.toLowerCase();
    // Явно «не в кэше» — как при ручной проверке
    if (htmlLower.indexOf('not in cache') !== -1 || htmlLower.indexOf('not available') !== -1 ||
        htmlLower.indexOf('could not fetch') !== -1 || htmlLower.indexOf('не сохранена в кэше') !== -1 ||
        htmlLower.indexOf('page is unavailable') !== -1 || htmlLower.indexOf('страница недоступна') !== -1) return 'No';
    // Как в ручной проверке: «Это кэш Google страницы …» или «This is Google's cache of …» и наш URL
    var isCacheOf = htmlLower.indexOf('cache of') !== -1 || htmlLower.indexOf('кэш google') !== -1 ||
        htmlLower.indexOf('кэш страницы') !== -1 || htmlLower.indexOf('google cache of') !== -1;
    var hasOurUrl = html.indexOf(normalizedForMatch) !== -1 || html.indexOf(pageUrl) !== -1;
    if (isCacheOf && hasOurUrl) return 'Yes';
    return 'No';
  } catch (e) {
    return 'No';
  }
}

function normUrlForIndex(url) {
  if (!url || !url.trim) return '';
  var u = url.trim().toLowerCase();
  u = u.replace(/^https?:\/\/(www\.)?/i, '').split('#')[0].split('?')[0].replace(/\/$/, '').trim();
  return u;
}

function tryGoogleSiteSearch(query, pageUrl, sitePart) {
  try {
    var searchUrl = 'https://www.google.com/search?q=' + encodeURIComponent(query);
    var response = UrlFetchApp.fetch(searchUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      validateHttpsCertificates: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
      }
    });
    var code = response.getResponseCode();
    if (code < 200 || code >= 300) return 'Error';
    var html = response.getContentText();
    if (!html || html.length < 100) return 'Error';
    var htmlLower = html.toLowerCase();
    if (htmlLower.indexOf('captcha') !== -1 || htmlLower.indexOf('unusual traffic') !== -1 ||
        htmlLower.indexOf('blocked') !== -1 || htmlLower.indexOf('automated queries') !== -1) {
      return 'Error';
    }
    var noResults = htmlLower.indexOf('did not match any documents') !== -1 ||
        htmlLower.indexOf('ничего не найдено') !== -1 ||
        (htmlLower.indexOf('no results found') !== -1 && htmlLower.indexOf('no results found for') === -1);
    if (noResults) return 'No';

    var ourNorm = normUrlForIndex(pageUrl);
    if (!ourNorm) return 'No';

    // 1) Прямое вхождение закодированного URL в /url?q=
    if (html.indexOf('/url?q=' + encodeURIComponent(pageUrl)) !== -1) return 'Yes';
    var encodedNorm = encodeURIComponent('https://' + ourNorm);
    if (html.indexOf('/url?q=' + encodedNorm) !== -1) return 'Yes';

    // 2) Парсим все /url?q=... (значение до & или " или ')
    var reUrlQ = /\/url\?q=([^&"'\s]+)/g;
    var m;
    while ((m = reUrlQ.exec(html)) !== null) {
      try {
        var raw = m[1].replace(/\+/g, ' ');
        var decoded = decodeURIComponent(raw);
        var decNorm = normUrlForIndex(decoded);
        if (decNorm === ourNorm) return 'Yes';
        // наш URL + query (например utm) в результатах
        if (decNorm.indexOf(ourNorm) === 0 && (decNorm.length === ourNorm.length || decNorm.charAt(ourNorm.length) === '?')) return 'Yes';
      } catch (e) {}
    }

    // 3) Все href с https?:// — на случай другого формата выдачи
    var reHref = /href=["'](https?:\/\/[^"']+)["']/gi;
    while ((m = reHref.exec(html)) !== null) {
      var hrefUrl = m[1].replace(/&amp;/g, '&');
      var hrefNorm = normUrlForIndex(hrefUrl);
      if (hrefNorm === ourNorm) return 'Yes';
      if (hrefNorm.indexOf(ourNorm) === 0 && (hrefNorm.length === ourNorm.length || hrefNorm.charAt(ourNorm.length) === '?')) return 'Yes';
    }

    // 4) Текстовое вхождение нашего пути в HTML (URL в сниппете)
    if (html.indexOf(ourNorm) !== -1 && (htmlLower.indexOf('b_algo') !== -1 || htmlLower.indexOf('search') !== -1)) {
      var idx = html.indexOf(ourNorm);
      var before = html.substring(Math.max(0, idx - 80), idx);
      if (before.indexOf('url?q=') !== -1 || before.indexOf('href=') !== -1 || before.indexOf('http') !== -1) return 'Yes';
    }
    // 5) Запасной вариант: страница выдачи без «нет результатов», наш URL есть в тексте (как при ручном site:)
    if (!noResults && html.length > 3000 && html.indexOf(ourNorm) !== -1) return 'Yes';
    return 'No';
  } catch (e) {
    return 'Error';
  }
}

function tryBingSiteSearch(query, pageUrl, sitePart) {
  try {
    var searchUrl = 'https://www.bing.com/search?q=' + encodeURIComponent(query);
    var response = UrlFetchApp.fetch(searchUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
      }
    });
    var code = response.getResponseCode();
    if (code < 200 || code >= 300) return 'Error';
    var html = response.getContentText();
    if (!html || html.length < 100) return 'Error';
    var htmlLower = html.toLowerCase();
    var noResultsPhrase = htmlLower.indexOf('no results found') !== -1 ||
        htmlLower.indexOf("we didn't find any results") !== -1 ||
        htmlLower.indexOf('ничего не найдено') !== -1 ||
        (htmlLower.indexOf('there are no results') !== -1 && htmlLower.indexOf('there are no results for') === -1);
    if (noResultsPhrase) return 'No';

    var ourNorm = normUrlForIndex(pageUrl);
    if (!ourNorm) return 'No';

    // Прямые совпадения в href
    function hrefStartsWith(hrefVal) {
      var i = html.indexOf('href="' + hrefVal);
      if (i !== -1) {
        var next = html.charAt(i + ('href="' + hrefVal).length);
        if (next === '"' || next === '?' || next === '&') return true;
      }
      i = html.indexOf("href='" + hrefVal);
      if (i !== -1) {
        var next = html.charAt(i + ("href='" + hrefVal).length);
        if (next === "'" || next === '?' || next === '&') return true;
      }
      return false;
    }
    if (hrefStartsWith(pageUrl) || hrefStartsWith('https://' + sitePart) || hrefStartsWith('http://' + sitePart)) return 'Yes';
    if (html.indexOf('href="' + pageUrl + '"') !== -1 || html.indexOf("href='" + pageUrl + "'") !== -1) return 'Yes';
    if (html.indexOf('href="https://' + sitePart + '"') !== -1 || html.indexOf('href="http://' + sitePart + '"') !== -1) return 'Yes';

    // Все href с https?:// — нормализуем и сравниваем (Bing часто оборачивает в redirect)
    var reHref = /href=["'](https?:\/\/[^"']+)["']/gi;
    var m;
    while ((m = reHref.exec(html)) !== null) {
      var hrefUrl = m[1].replace(/&amp;/g, '&');
      var hrefNorm = normUrlForIndex(hrefUrl);
      if (hrefNorm === ourNorm) return 'Yes';
      if (hrefNorm.indexOf(ourNorm) === 0 && (hrefNorm.length === ourNorm.length || hrefNorm.charAt(ourNorm.length) === '?')) return 'Yes';
    }

    // Bing: наш путь встречается на странице результатов
    if (html.indexOf(ourNorm) !== -1 && (html.indexOf('b_algo') !== -1 || html.indexOf('b_ans') !== -1)) return 'Yes';
    return 'No';
  } catch (e) {
    return 'Error';
  }
}

function fetchAndCheck(pageUrl, targetUrl, exactAnchor) {
  try {
    var response = UrlFetchApp.fetch(pageUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; AnchorChecker/1.0)' }
    });
    var code = response.getResponseCode();
    if (code < 200 || code >= 300) {
      return 'Error';
    }
    var html = response.getContentText();
    var baseUrl = response.getHeaders()['Content-Location'] || pageUrl;
    var resolvedBase = resolveBase(pageUrl);

    var found = findLinkInHtml(html, resolvedBase, targetUrl, exactAnchor);
    return found ? 'Yes' : 'No';
  } catch (e) {
    return 'Error';
  }
}

function resolveBase(pageUrl) {
  try {
    var afterProtocol = pageUrl.indexOf('://');
    if (afterProtocol < 0) return pageUrl;
    var firstSlash = pageUrl.indexOf('/', afterProtocol + 3);
    if (firstSlash < 0) return pageUrl;
    return pageUrl.substring(0, firstSlash);
  } catch (e) {
    return pageUrl;
  }
}

function normalizeUrl(url) {
  if (!url || !url.trim()) return '';
  var u = url.trim();
  var hash = u.indexOf('#');
  if (hash >= 0) u = u.substring(0, hash);
  var end = u.length;
  if (u.charAt(end - 1) === '/' && u.length > 1 && u.indexOf('/', 8) !== -1) {
    var pathStart = u.indexOf('/', 8);
    if (pathStart >= 0 && pathStart < end - 1) {
      u = u.substring(0, end - 1);
    }
  }
  return u;
}

function resolveHref(href, base) {
  href = href.trim();
  if (href.indexOf('http://') === 0 || href.indexOf('https://') === 0) return href;
  if (href.indexOf('//') === 0) return 'https:' + href;
  if (href.indexOf('/') === 0) {
    var slash = base.indexOf('/', 8);
    var origin = slash > 0 ? base.substring(0, slash) : base;
    return origin + href;
  }
  var lastSlash = base.lastIndexOf('/');
  var baseDir = lastSlash > 8 ? base.substring(0, lastSlash + 1) : base + '/';
  return baseDir + href;
}

function normalizeAnchor(text) {
  if (text == null) return '';
  return text.toString()
    .replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function decodeHtmlEntities(str) {
  if (!str) return '';
  return str
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&nbsp;/gi, ' ')
    .replace(/&#(\d+);/g, function(_, n) { return String.fromCharCode(parseInt(n, 10)); })
    .replace(/&#x([0-9a-f]+);/gi, function(_, n) { return String.fromCharCode(parseInt(n, 16)); });
}

function stripTags(html) {
  return html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
}

function urlsMatch(pageUrl, targetUrl) {
  var a = normalizeUrl(pageUrl);
  var b = normalizeUrl(targetUrl);
  if (a === b) return true;
  var aNoQuery = a.split('?')[0];
  var bNoQuery = b.split('?')[0];
  if (aNoQuery === bNoQuery) return true;
  if (a.indexOf(b) === 0 && (a.length === b.length || a.charAt(b.length) === '?' || a.charAt(b.length) === '#')) return true;
  if (b.indexOf(a) === 0 && (b.length === a.length || b.charAt(a.length) === '?' || b.charAt(a.length) === '#')) return true;
  return false;
}

function findLinkInHtml(html, baseUrl, targetUrl, exactAnchor) {
  var targetNorm = normalizeUrl(targetUrl);
  var anchorNorm = normalizeAnchor(exactAnchor);

  var re = /<a\s[^>]*href\s*=\s*["']([^"']*)["'][^>]*>([\s\S]*?)<\/a>/gi;
  var m;
  while ((m = re.exec(html)) !== null) {
    var href = m[1];
    if (!href || href.indexOf('#') === 0) continue;
    var fullHref = resolveHref(href.trim(), baseUrl);
    if (!urlsMatch(fullHref, targetUrl)) continue;
    var linkText = stripTags(m[2]);
    linkText = decodeHtmlEntities(linkText);
    if (normalizeAnchor(linkText) === anchorNorm) return true;
  }
  return false;
}
