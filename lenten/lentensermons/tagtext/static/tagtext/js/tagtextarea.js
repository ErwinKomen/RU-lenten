(function ($) {
  'use strict';

  var loc_tribute = null;

  $(document).ready(function () {
    // Make sure the use_tribute is used
    // Initialize tribute on all elements that need it
    // See: https://github.com/zurb/tribute
    $(".use_tribute").each(function (idx, elThis) {
      var sTclass = $(elThis).attr("tclass"),
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
                  ru.lenten.seeker.get_tribute(text, sTclass, users => cb(users));
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
          idx = 0,
          tagnum = 0,
          num_tags = 0,
          sValue = "",
          arNode = [],
          arPart = [],
          sJson = "",
          elPrev = $(elThis).prev();

      // Convert the HTML into a list
      html = $.parseHTML($(elThis).html());
      $.each(html, function (idx, elThis) {
        switch (elThis.nodeType) {
          case 1: // is it <span>?
            if (elThis.nodeName === "SPAN") {
              arNode.push(
                {
                  "type": "tag",
                  "value": elThis.textContent,
                  "tagid": elThis.attributes["tagid"].value
                }
                );
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
    });

  });
  
})(django.jQuery)