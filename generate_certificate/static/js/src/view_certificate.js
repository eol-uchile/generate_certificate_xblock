/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function CertificateLinkXBlock(runtime, element) {
    var $ = window.jQuery;
    var $element = $(element);
    var handlerUrl = runtime.handlerUrl(element, 'certificate_data');

    $(element).find("#btn_generate_cert").live('click', function(e) {
    // this retrieves the data-endpoint generated in the html at the moment of the click and sends a POST method 
    // with all the data, if it is correct it goes to showUrl and if not it goes to errorCertificate        
        var data = e.target.getAttribute('data-endpoint')
        if (data !== undefined ){
            $.ajax({
                type: "POST",
                url: data,
                success: showUrl,
                error: errorCertificate,         
            });
        }        
    });

    function showUrl(result){
        // unlike the previous one, this one retrieves directly the url that generates the button and when it has it, it sends it to 
        // to viewCertificate   
        $(element).find("#btn_generate_cert").hide();
        $.post(handlerUrl, JSON.stringify({}))
        .done(viewCertificate)
        .fail(errorCertificate)    
        
    }

    function viewCertificate(result){
        // this function retrieves all the data in general and creates the new button that will open the new sale with the certificate.
        if(result.cert == "") 
            showUrl()
            
        else{
            var botonUrl = result.cert;
            var nuevoBoton = document.createElement("button");
            nuevoBoton.textContent = "Ver Certificado";
            nuevoBoton.className = "btn generate_certs";
            nuevoBoton.onclick = function(){
                window.open(botonUrl, "_blank");       
            }
            var contenedorBoton = $(element).find(".msg-actions");
            contenedorBoton.append(nuevoBoton);
        }     
    };


    function errorCertificate(result){
        // if an error occurs, it comes directly here, where it leaves an error message
        $(element).find(".btn.generate_certs").hide();
        $("#error-message").show();
    }

}
