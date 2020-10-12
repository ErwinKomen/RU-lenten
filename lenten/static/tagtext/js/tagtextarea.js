(function ($) {
  'use strict';

  var loc_tribute = null;

  /**
   * get_tribute
   *    Remotely get tribute informatino
   *
   */
  function get_tagtext_tribute(sRemote, text, sTclass, cb) {
    var sUrl = "",
        xhr = new XMLHttpRequest(),
        base_url = "";

    try {
      // Do we have a remote?
      if (sRemote === "") {
        // Get the base URL
        base_url = $("#__baseurl__").text();
        // Get the real URL 
        sUrl = base_url + 'api/tributes/';
      } else {
        sUrl = sRemote;
      }
      // Fill in the XHR
      xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
          if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            cb(data);
          } else if (xhr.status === 403) {
            cb([]);
          }
        }
      };

      // Adapt the URL
      if (sUrl.indexOf("?") < 0) {
        // The URL does not contain additional information yet
        sUrl = sUrl + "?tclass=" + sTclass + "&q=" + text;
      } else {
        // The URL itself already contains subcategorization
        sUrl = sUrl + "&q=" + text;
      }

      xhr.open("GET", sUrl, true);
      xhr.send();
    } catch (ex) {
      errMsg("get_tagtext_tribute", ex);
    }
  }

  function errMsg(sMsg, ex) {
    var sHtml = "",
        sMsg = "";

    if (ex === undefined) {
      sHtml = "Error: " + sMsg;
    } else {
      sHtml = "Error in [" + sMsg + "]<br>" + ex.message;
    }
    console.log(sHtml);
  }


  $(document).ready(function () {
    // Make sure the use_tribute is used
    // Initialize tribute on all elements that need it
    // See: https://github.com/zurb/tribute
    $(".use_tribute").each(function (idx, elThis) {
      var sTclass = "",       // value of 'tclass' variable
          sRemote = "",       // Remote URL to call
          loc_tribute = null;

      sTclass = $(elThis).attr("tclass");
      sRemote = $(elThis).attr("remote");
      loc_tribute = new Tribute({
            collection: [
              {
                trigger: "@",
                selectTemplate: function (item) {
                  return ('<span contenteditable="false" tagid="' + item.original.id + '">' +
                    item.original.value +
                    '</span>');
                },
                lookup: 'name',
                fillAttr: 'name',
                values: function (text, cb) {
                  // Try to make this more generic. But how???
                  // ru.lenten.seeker.get_tribute(text, sTclass, users => cb(users));
                  get_tagtext_tribute(sRemote, text, sTclass, users => cb(users));
                },
                menuItemTemplate: function (item) {
                  return item.string;
                }
              }
            ]
          });
      // Attach it
      loc_tribute.attach(elThis);
    });
    // Make sure the contents of each use_tribute div are copied to the nearest <textarea> preceding
    $(".use_tribute").on("blur", function () {
      var elThis = $(this),
          html = null,
          part = null,
          div = null,
          idx = 0,
          jdx = 0,
          tagnum = 0,
          num_tags = 0,
          sValue = "",
          arNode = [],
          arPart = [],
          sJson = "",
          elPrev = $(elThis).prev();

      try {
        // Convert the HTML into a list
        if ($(elThis).find("div").length > 0) {
          html = [];
          part = $(elThis).find("div");
          for (idx = 0; idx < part.length; idx++) {
            div = $.parseHTML($(part[idx]).html());
            for (jdx = 0; jdx < div.length; jdx++) {
              html.push(div[jdx]);
            }
            // ALso add a break
            html.push($("<br>")[0]);
          }
        } else {
          html = $.parseHTML($(elThis).html());
        }

        $.each(html, function (idx, elThis) {
          switch (elThis.nodeType) {
            case 1: // is it <span>?
              switch (elThis.nodeName) {
                case "SPAN":
                  arNode.push(
                    {
                      "type": "tag",
                      "value": elThis.textContent,
                      "tagid": elThis.attributes["tagid"].value
                    });
                  break;
                case "BR":
                  arNode.push({ "type": "text", "value": "\n" });
                  break;
              }
              break;
            case 3: // Text
              // Does this contain new tags?
              sValue = elThis.nodeValue;
              arPart = sValue.split("@");
              if (arPart.length > 1 && arPart.length % 2 !== 0) {
                // Walk all parts: every odd number is a tag
                for (idx = 0; idx < arPart.length; idx++) {
                  if (idx % 2 === 0) {
                    // Even number: text
                    arNode.push({ "type": "text", "value": arPart[idx] });
                  } else {
                    // Odd number: new tag
                    arNode.push({ "type": "new", "value": arPart[idx] });
                  }
                }
                // Calculate how many tags we have
                num_tags = (arPart.length - 1) / 2;
              } else {
                arNode.push({ "type": "text", "value": sValue });
              }
              break;
          }
        });
        // Convert the list into a stringified JSON
        sJson = JSON.stringify(arNode);
        // Copy the JSON to the <textarea>
        $(elPrev).html(sJson);
      } catch (ex) {
        errMsg("get_tagtext_tribute", ex);
      }
    });

  });


  
})(django.jQuery)