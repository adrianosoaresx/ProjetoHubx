(function(){
  const el = document.querySelector('[data-i18n]');
  let texts = {};
  if(el){
    try{
      texts = JSON.parse(el.dataset.i18n);
    }catch(e){
      texts = {};
    }
  }
  window.chatTexts = texts;
})();
