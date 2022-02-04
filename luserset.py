import debug

class luserset(set):
    def __init__(self, *args):
        super().__init__(*args)

    name_to_id = dict()

    def associate_name(self, id_, name):
        """ associate a name to an id """
        debug.dlog(f"associating {name} to {id_}")
        self.name_to_id[name] = id_

    def check_for_name(self, name):
        """ lookup the id associated with the name, return whether the id is in the set """
        id = self.name_to_id.get(name, None)
        return True if id != None else False

    def difference(self, other_set):
        """ map names in other_set to addresses, remove the names if addresses exist here """
        debug.dlog(self.name_to_id)
        mapped_set = set()
        for name in other_set:
            if self.check_for_name(name) == False:
                if name not in self:
                    mapped_set.add(name) # keep, no intersection
        return mapped_set
