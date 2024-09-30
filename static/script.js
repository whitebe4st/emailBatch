$(document).ready(function() {
    let emailList = [];
    let attachmentFilename = '';

    // Add email to the list
    $('#add-email-btn').click(function() {
        let email = $('#email-input').val().trim();
        if (email) {
            emailList.push(email);
            updateEmailList();
            $('#email-input').val('');
        }
    });

    // Handle Enter key for adding email
    $('#email-input').keypress(function(e) {
        if (e.which == 13) {
            $('#add-email-btn').click();
            return false;
        }
    });

    // Upload CSV file
    $('#csv-file').change(function() {
        let file = this.files[0];
        if (file) {
            let formData = new FormData();
            formData.append('csv_file', file);

            $.ajax({
                url: '/upload_csv',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                success: function(response) {
                    emailList = emailList.concat(response.emails);
                    updateEmailList();
                    $('#csv-file').val('');
                },
                error: function(xhr) {
                    alert(xhr.responseJSON.error);
                    $('#csv-file').val('');
                }
            });
        }
    });

    // Upload attachment
    $('#attachment-file').change(function() {
        let file = this.files[0];
        if (file) {
            let formData = new FormData();
            formData.append('attachment', file);

            $.ajax({
                url: '/upload_attachment',
                type: 'POST',
                data: formData,
                contentType: false,
                processData: false,
                success: function(response) {
                    attachmentFilename = response.filename;
                },
                error: function(xhr) {
                    alert(xhr.responseJSON.error);
                    $('#attachment-file').val('');
                }
            });
        }
    });

    // Send emails
    $('#send-emails-btn').click(function() {
        let subject = $('#subject').val().trim();
        let body = $('#body').val().trim();

        if (!subject || !body) {
            alert('Please provide a subject and body for the email.');
            return;
        }

        if (emailList.length === 0) {
            alert('Email list is empty.');
            return;
        }

        let data = {
            email_list: emailList,
            subject: subject,
            body: body,
            attachment: attachmentFilename
        };

        $('#send-emails-btn').prop('disabled', true);
        $('#status-message').removeClass().addClass('alert alert-info').text('Sending emails...').show();

        $.ajax({
            url: '/send_emails',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                $('#status-message').removeClass().addClass('alert alert-success').text(response.message);
                $('#send-emails-btn').prop('disabled', false);
            },
            error: function(xhr) {
                $('#status-message').removeClass().addClass('alert alert-danger').text(xhr.responseJSON.error);
                $('#send-emails-btn').prop('disabled', false);
            }
        });
    });

    // Update email list UI
    function updateEmailList() {
        $('#email-list').empty();
        emailList.forEach(function(email, index) {
            let listItem = $('<li>').addClass('list-group-item d-flex justify-content-between align-items-center').text(email);
            let deleteBtn = $('<button>').addClass('btn btn-sm btn-danger').text('Delete').click(function() {
                emailList.splice(index, 1);
                updateEmailList();
            });
            listItem.append(deleteBtn);
            $('#email-list').append(listItem);
        });
    }
});
