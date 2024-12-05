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