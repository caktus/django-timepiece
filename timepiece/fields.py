from django import forms


class UserModelChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return obj.get_name_or_username()


class UserModelMultipleChoiceField(forms.ModelMultipleChoiceField):

    def label_from_instance(self, obj):
        return obj.get_name_or_username()
