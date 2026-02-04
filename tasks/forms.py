from django import forms
import os

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel faylni tanlang (.xlsx)",
        help_text="Fayl ustunlari: Title, Description, Deadline, Priority",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )

    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')
        ext = os.path.splitext(file.name)[1]
        valid_extensions = ['.xlsx', '.xls']
        if not ext.lower() in valid_extensions:
            raise forms.ValidationError("Iltimos, faqat Excel (.xlsx) formatidagi fayl yuklang.")
        return file