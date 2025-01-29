def year_selection(self):
    """
    Never change this helper function !!!!!!!!!
    It has impact in database .
    """
    year = 2010  # replace 2000 with your a start year
    year_list = []
    while year != 2099:  # replace 2030 with your end year
        year_list.append((str(year), str(year)))
        year += 1
    return year_list

def month_selection(self):
    """
    Returns a list of months in the format [(1, 'January'), ..., (12, 'December')]
    """
    return [
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
