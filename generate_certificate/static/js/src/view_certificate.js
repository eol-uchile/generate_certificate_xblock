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
    var handlerUrlRege = runtime.handlerUrl(element, 'regenerate_certificate_for_user');
    // generate certificate
    $(element).find("#btn_generate_cert").live('click', function(e) {
        $(this).prop('disabled', true) 

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
        // this function retrieves all the data in general and creates the new button that will open the new sale with the certificate
        // and creates a new button regenerate certificate that allows you to update the certificate.
        if(result.cert == "") 
            setTimeout(showUrl(), 3000)
            
        else{
            if ($(element).find("#view_cert").length){
                $(element).find("#view_cert")[0].href = result.cert
                $(element).find("#rege_cert").text("Regenerado exitosamente");
                $(element).find("#btn_rege_cert").prop('disabled',false)    
            }
            else{
                var botonUrl = result.cert;
                var nuevoBoton = document.createElement("a");
                nuevoBoton.textContent = "Ver Certificado";
                nuevoBoton.id = "view_cert"
                nuevoBoton.className = "btn generate_certs";
                nuevoBoton.href = botonUrl;
                nuevoBoton.target="_blank"
                var contenedorBoton = $(element).find(".msg-actions");
                contenedorBoton.append(nuevoBoton);
                
                var nuevoBotonRege = document.createElement("button");
                nuevoBotonRege.textContent=  "Regenerar Certificado";
                nuevoBotonRege.className = "btn generate_certs"
                nuevoBotonRege.id="btn_rege_cert";
                contenedorBoton.append(nuevoBotonRege);
                
            }
        }     
    };


    function errorCertificate(result){
        // if an error occurs, it comes directly here, where it leaves an error message
        $(element).find(".btn.generate_certs").hide();
        $("#error-message").show();
    }

    $(element).find("#btn_rege_cert").live('click', function(e) {
        // search for the button, if it exists extract the url if it is correct send it to showUrl. It also disables the button to avoid bugging the code.
        $(element).find("#rege_cert").text("Regenerando su Certificado")
        $(this).prop('disabled', true) 
        $.post(handlerUrlRege, JSON.stringify({}))
        .done(showUrl)
        .fail(errorCertificate)                     
        });
}
