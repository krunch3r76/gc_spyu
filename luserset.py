import debug

class luserset(set):
    def __init__(self, *args):
        super().__init__(*args)

    name_to_id = dict()

    def associate_name(self, id_, name):
        """ associate a name to an id """
        # debug.dlog(f"associating {name} to {id_}")
        self.name_to_id[name] = id_

    def check_for_name(self, name):
        """ lookup the id associated with the name, return whether the id is in the set """
        id = self.name_to_id.get(name, None)
        return True if id != None else False

    def check_for_partial_address(self, addressPartial):
        """ lookup the id associated with the partial address and return whether id is in the set """
        for element in self:
            if element.startswith(addressPartial):
                return True
        return False

    def difference(self, other_set):
        """ map names in other_set to addresses, remove the names if addresses exist here """
        mapped_set = set() # final set considering names first
        mapped_names_set = set()
        for name in other_set:
            if self.check_for_name(name) == False:
                if name not in self:
                    mapped_names_set.add(name) # keep, no intersection
        # now see if it is an address that matches
        for addr in mapped_names_set:
            if not self.check_for_partial_address(addr):
                mapped_set.add(addr)

        return mapped_set
