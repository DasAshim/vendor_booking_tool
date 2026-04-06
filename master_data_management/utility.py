from master_data_management.models import Company


def get_company_info():
    """
    Returns a company .
    """
    queryset = Company.objects.values('id', 'name')
    company_dict = {c['id']: c['name'] for c in queryset}
    return company_dict
