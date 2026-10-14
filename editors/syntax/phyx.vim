" Vim syntax file
" Language: φyrx (PhyrxScript / PhyrexianScript)
" Filenames: *.phyx *.vphyx

if exists('b:current_syntax')
  finish
endif

syn match phyxShebang '^#!.*$'
syn match phyxComment '\^rukx.*$'
syn region phyxString start='"' skip='\\\\.' end='"' contains=phyxEscape
syn match phyxEscape '\\\\[\\"nt]' contained
syn match phyxNumber '\<əx\\?[0-9][0-9a-fA-F]*\>'
syn match phyxPunct '[\^!?.,:\-]'
syn match phyxMarker '\%(baqilx\|aχəw'\|baxuφ\|ǩaπa\|qit\|'u\|ba\|bu\|lo\|xe\|ťe\|əx\%)'
syn match phyxVerb '\%(ǩeǆylqitsodraam\|ǩeǆylqitsodreem\|ǩeǆylqitsodram\|ǩeǆylqitsodrem\|ǩeǆylqitsodrom\|ǩeǆylqitsodrym\|ǩeǆylqitsodrøm\|ǩeǆylqiťsodram\|ǩeǆylqiťsodrum\|ǩeǆylqytsodram\|ǩeǆylqytsodrem\|ǩeǆylqytsodrum\|ǩeǆylqitsodrm\|ǩeǆylqytsodrm\|'iixtfu'aaq\|'iixtfu'eeq\|čtəčpliɣaan\|čtəčpliɣeen\|'iixtfu'aq\|'iixtfu'aǧ\|'iixtfu'eq\|'iixtfu'oq\|'iixtfu'yq\|'iixtfu'øq\|'iixťfu'aq\|'iixťfu'uq\|'iyxtfu'aq\|'iyxtfu'eq\|'iyxtfu'uq\|rukxtekaat\|rukxtekeet\|čtəčpliɣan\|čtəčpliɣen\|čtəčpliɣon\|čtəčpliɣyn\|čtəčpliɣøn\|čtəčplyɣan\|čtəčplyɣen\|čtəčplyɣun\|čtəčπliɣan\|čtəčπliɣun\|əxķus'əaar\|əxķus'əeer\|'iixtfu'q\|'iyxtfu'q\|'iţpənaan\|'iţpəneen\|rukxtekat\|rukxtekať\|rukxteket\|rukxtekot\|rukxtekyt\|rukxtekøt\|rukxteǩat\|rukxteǩut\|rukxtøkat\|rukxtøket\|rukxtøkut\|čtəčpliɣn\|čtəčplyɣn\|əxķus'əar\|əxķus'əer\|əxķus'əor\|əxķus'əur\|əxķus'əyr\|əxķus'əør\|ɬšeɴazaav\|ɬšeɴazeev\|'iţpənan\|'iţpənen\|'iţpənon\|'iţpənyn\|'iţpənøn\|'iţπənan\|'iţπənun\|'yţpənan\|'yţpənen\|'yţpənun\|'ətsxaan\|'ətsxeen\|brøtjaat\|brøtjeet\|grmɒɣaag\|grmɒɣeeg\|korxgaar\|korxgeer\|rukxtekt\|rukxtøkt\|ķus'əaar\|ķus'əeer\|ǆ'ynpaap\|ǆ'ynpeep\|əxķus'ər\|ɬšeɴazav\|ɬšeɴazev\|ɬšeɴazov\|ɬšeɴazuv\|ɬšeɴazyv\|ɬšeɴazøv\|ɬšøɴazav\|ɬšøɴazev\|ɬšøɴazuv\|ʁšθakaaɴ\|ʁšθakeeɴ\|χɬkevaak\|χɬkeveek\|'iţpənn\|'yţpənn\|'ətsxan\|'ətsxen\|'ətsxon\|'ətsxun\|'ətsxyn\|'ətsxøn\|'əťsxan\|'əťsxun\|asəraaθ\|asəreeθ\|brøtjat\|brøtjať\|brøtjet\|brøtjot\|brøtjut\|brøtjyt\|brøtjøt\|brøťjat\|brøťjut\|bɬølaaπ\|bɬøleeπ\|grmɒɣag\|grmɒɣeg\|grmɒɣog\|grmɒɣug\|grmɒɣyg\|grmɒɣøg\|korxgar\|korxger\|korxgor\|korxgur\|korxgyr\|korxgør\|krepaag\|krepeeg\|mɴyraax\|mɴyreex\|pən'aag\|pən'eeg\|raφoaaj\|raφoeej\|tluxaat\|tluxeet\|čxətaa'\|čxətee'\|ķus'əar\|ķus'əer\|ķus'əor\|ķus'əur\|ķus'əyr\|ķus'əør\|ǆ'ynpap\|ǆ'ynpaπ\|ǆ'ynpep\|ǆ'ynpop\|ǆ'ynpup\|ǆ'ynpyp\|ǆ'ynpøp\|ǆ'ynπap\|ǆ'ynπup\|ǩorxgar\|ǩorxgur\|ɢnagaaɮ\|ɢnageeɮ\|ɬšeɴazv\|ɬšøɴazv\|ʁšθakaɴ\|ʁšθakeɴ\|ʁšθakoɴ\|ʁšθakuɴ\|ʁšθakyɴ\|ʁšθakøɴ\|ʁšθaǩaɴ\|ʁšθaǩuɴ\|χɬkevak\|χɬkevaǩ\|χɬkevek\|χɬkevok\|χɬkevyk\|χɬkevøk\|χɬkøvak\|χɬkøvek\|χɬkøvuk\|χɬǩevak\|χɬǩevuk\|'uxaaq\|'uxeeq\|'uɬaač\|'uɬeeč\|'ətsxn\|asəraθ\|asəreθ\|asəroθ\|asəruθ\|asəryθ\|asərøθ\|babaag\|babeeg\|brøtjt\|bukaað\|bukeeð\|bɬølaπ\|bɬølaφ\|bɬøleπ\|bɬøloπ\|bɬøluπ\|bɬølyπ\|bɬøløπ\|gefaat\|gefeet\|grmɒɣg\|korxgr\|krepag\|krepeg\|krepog\|krepyg\|krepøg\|kreπag\|kreπug\|krøpag\|krøpeg\|krøpug\|lu'aaf\|lu'eef\|lupaas\|lupees\|mɒɣaag\|mɒɣeeg\|mɴyrax\|mɴyrex\|mɴyrox\|mɴyrux\|mɴyryx\|mɴyrøx\|naķaam\|naķeem\|pihaaš\|piheeš\|pən'ag\|pən'eg\|pən'og\|pən'ug\|pən'yg\|pən'øg\|qabaa'\|qabee'\|raφoaj\|raφoej\|raφooj\|raφouj\|raφoyj\|raφoøj\|ronaaɣ\|roneeɣ\|samaak\|sameek\|tapaaq\|tapeeq\|tekaat\|tekeet\|tluxat\|tluxať\|tluxet\|tluxot\|tluxut\|tluxyt\|tluxøt\|tøwaap\|tøweep\|xušaav\|xušeev\|čxəta'\|čxəte'\|čxəto'\|čxətu'\|čxəty'\|čxətø'\|čxəťa'\|čxəťu'\|ķus'ər\|ţə'aa'\|ţə'ee'\|ťewaan\|ťeween\|ťluxat\|ťluxut\|ǆ'ynpp\|ɢnagaɮ\|ɢnageɮ\|ɢnagoɮ\|ɢnaguɮ\|ɢnagyɮ\|ɢnagøɮ\|ɣɒzaaɢ\|ɣɒzeeɢ\|ʁšθakɴ\|πøkaak\|πøkeek\|πən'ag\|πən'ug\|χɬkevk\|χɬkøvk\|'uxaq\|'uxaǧ\|'uxeq\|'uxoq\|'uxuq\|'uxyq\|'uxøq\|'uɬač\|'uɬeč\|'uɬoč\|'uɬuč\|'uɬyč\|'uɬøč\|asərθ\|babag\|babeg\|babog\|babug\|babyg\|babøg\|bukað\|bukeð\|bukoð\|bukuð\|bukyð\|bukøð\|buǩað\|buǩuð\|bɬølπ\|gefat\|gefať\|gefet\|gefot\|gefut\|gefyt\|geføt\|gøfat\|gøfet\|gøfut\|krepg\|krøpg\|lu'af\|lu'ef\|lu'of\|lu'uf\|lu'yf\|lu'øf\|lupas\|lupes\|lupos\|lupus\|lupys\|lupøs\|luπas\|luπus\|mɒɣag\|mɒɣeg\|mɒɣog\|mɒɣug\|mɒɣyg\|mɒɣøg\|mɴyrx\|naķam\|naķem\|naķom\|naķum\|naķym\|naķøm\|pihaš\|piheš\|pihoš\|pihyš\|pihøš\|pyhaš\|pyheš\|pyhuš\|pən'g\|qaba'\|qabe'\|qabo'\|qabu'\|qaby'\|qabø'\|raφoj\|ronaɣ\|roneɣ\|ronoɣ\|ronuɣ\|ronyɣ\|ronøɣ\|samak\|samaǩ\|samek\|samok\|samuk\|samyk\|samøk\|tapaq\|tapaǧ\|tapeq\|tapoq\|tapuq\|tapyq\|tapøq\|taπaq\|taπuq\|tekat\|tekať\|teket\|tekot\|tekyt\|tekøt\|teǩat\|teǩut\|tluxt\|tøkat\|tøket\|tøkut\|tøwap\|tøwaπ\|tøwep\|tøwop\|tøwup\|tøwyp\|tøwøp\|xušav\|xušev\|xušov\|xušuv\|xušyv\|xušøv\|čxət'\|ţewan\|ţewun\|ţə'a'\|ţə'e'\|ţə'o'\|ţə'u'\|ţə'y'\|ţə'ø'\|ťewan\|ťewen\|ťewon\|ťewyn\|ťewøn\|ťøwan\|ťøwap\|ťøwen\|ťøwun\|ťøwup\|ǧaba'\|ǧabu'\|ɢnagɮ\|ɣɒzaɢ\|ɣɒzeɢ\|ɣɒzoɢ\|ɣɒzuɢ\|ɣɒzyɢ\|ɣɒzøɢ\|πihaš\|πihuš\|πøkak\|πøkaǩ\|πøkek\|πøkok\|πøkuk\|πøkyk\|πøkøk\|πøǩak\|πøǩuk\|'uxq\|'uɬč\|babg\|bukð\|daal\|deel\|geft\|gøft\|lu'f\|lups\|mɒɣg\|naķm\|pihš\|pyhš\|qab'\|ronɣ\|samk\|tapq\|tekt\|tøkt\|tøwp\|xušv\|ţə''\|ťewn\|ťøwn\|əaax\|əeex\|ɣɒzɢ\|πøkk\|dal\|del\|dol\|dul\|dyl\|døl\|əax\|əex\|əox\|əux\|əyx\|əøx\|dl\|xə\|ðə\|əx\%)'
syn match phyxConstant '\%(əixiww\|əxbytp\|bytp\|'ii\|ķi\|ķu\%)'

hi def link phyxShebang Comment
hi def link phyxComment Comment
hi def link phyxString String
hi def link phyxEscape SpecialChar
hi def link phyxNumber Number
hi def link phyxPunct Delimiter
hi def link phyxMarker Keyword
hi def link phyxVerb Operator
hi def link phyxConstant Constant

let b:current_syntax = 'phyx'
