import webbrowser
from graphviz import Digraph

from ..shopcore.shop_api import get_attribute_value, get_xyt_attribute, get_attribute_info, \
    set_attribute, get_object_info


# This check can be used to stops infinite recursion in some debuggers when stepping into __init__. Debuggers can call
# __dir__ before/during the initialization, and if any class attributes are referred to in both __dir__ and __getattr__
# the call to dir will invoke __getattr__, which in turn will call itself indefinitely
def is_private_attr(attr):
    return attr[0] == '_'


class ModelBuilderType(object):
    def __init__(self, shop_api):
        self._shop_api = shop_api
        self._all_types = [object_type for object_type in shop_api.GetObjectTypeNames()
                           if shop_api.GetObjectInfo(object_type, 'isInput')]
        self._types = []
        self.update()

    def __getattr__(self, object_type):
        # Recursion guard
        if is_private_attr(object_type):
            return

        if self._shop_api.UpdateNeeded():
            self.update()
        return self._types[object_type]

    def __dir__(self):
        return [object_type for object_type in self._types] + [x for x in super().__dir__() if x[0] != '_'
                                                               and x not in self._types]

    def __getitem__(self, item):
        return self.__getattr__(item)

    def update(self):
        objects = {object_type: [] for object_type in self._all_types}
        for object_name, object_type in zip(self._shop_api.GetObjectNamesInSystem(),
                                            self._shop_api.GetObjectTypesInSystem()):
            objects[object_type].append(object_name)
        self._types = {object_type: ModelBuilderObject(self._shop_api, self, object_type, object_names)
                       for object_type, object_names in objects.items()}

    def build_connection_tree(self, filename='topology', write_file=False):
        types = ['reservoir', 'plant', 'gate', 'junction', 'junction_gate', 'creek_intake', 'tunnel']
        relation_types = ['connection_standard', 'connection_spill', 'connection_bypass']
        object_types = self._shop_api.GetObjectTypesInSystem()
        object_names = self._shop_api.GetObjectNamesInSystem()
        dot = Digraph(comment='SHOP topology')
        connections = []
        networks = []
        subgraphs = []
        for i, (name, object_type) in enumerate(zip(object_names, object_types)):
            if object_type in types:
                shape = 'ellipse'
                bgcolor = 'none'
                subgraph = None
                if object_type == 'plant':
                    shape = 'box'
                    bgcolor = 'rosybrown1'
                elif object_type == 'reservoir':
                    shape = 'invtriangle'
                    bgcolor = 'skyblue'
                    added_to_network = self._shop_api.GetIntValue(object_type, name, "added_to_network")
                    if added_to_network:
                        network_no = self._shop_api.GetIntValue(object_type, name, "network_no")
                        if network_no not in networks:
                            networks.append(network_no)
                            s = Digraph(comment='Network')
                            s.attr(rank='same')
                            subgraphs.append(s)
                        subgraph = subgraphs[networks.index(network_no)]
                elif object_type == 'junction' or object_type == 'junction_gate':
                    shape = 'point'
                elif object_type == 'tunnel':
                    shape = 'box'
                    bgcolor = 'gray83'
                dot.node('{0}_{1}'.format(object_type, name), label=name, shape=shape, style='filled',
                         fillcolor=bgcolor)
                if subgraph is not None:
                    subgraph.node('{0}_{1}'.format(object_type, name), label=name, shape=shape, style='filled',
                                  fillcolor=bgcolor)
                for relation in relation_types:
                    for connection in self._shop_api.GetRelations(object_type, name, relation):
                        connections.append((i, connection, relation))
        for connection in connections:
            if (object_types[connection[0]] == 'gate' or object_types[connection[1]] == 'gate') \
                    and connection[2] != 'connection_standard':
                dot.attr('edge', style='dashed')
            else:
                dot.attr('edge', style='solid', arrowtail='none', arrowhead='none')
            dot.edge('{0}_{1}'.format(object_types[connection[0]], object_names[connection[0]]),
                     '{0}_{1}'.format(object_types[connection[1]], object_names[connection[1]]))
        for s in subgraphs:
            dot.subgraph(s)          
        if write_file:
            dot.render(filename + '.gv', view=True)
        return dot


class ModelBuilderObjectIterator(object):
    def __init__(self, model_builder_object):
        self._model_builder_object = model_builder_object
        self._index = 0

    def __next__(self):
        if self._index < len(self._model_builder_object.get_object_names()):
            self._index += 1
            return self._model_builder_object.__getattr__(
                self._model_builder_object.get_object_names()[self._index - 1])
        raise StopIteration


class ModelBuilderObject(object):
    def __init__(self, shop_api, parent, object_type, object_names):
        self._shop_api = shop_api
        self._parent = parent
        self._type = object_type
        self._names = object_names
        self.attributes = {}

    def __getattr__(self, name):
        # Recursion guard
        if is_private_attr(name):
            return

        if name in self._names:
            if name not in self.attributes:
                attribute = AttributeBuilderObject(self._shop_api, self._type, name)
                self.attributes[name] = attribute
            return self.attributes[name]
        else:
            raise AttributeError()

    def __dir__(self):
        return [x for x in super().__dir__() if x[0] != '_'] + self._names

    def __getitem__(self, item):
        return self.__getattr__(item)

    def add_object(self, name):
        self._shop_api.AddObject(self._type, name)
        if name in self._shop_api.GetObjectNamesInSystem():
            self._add_object_name(name)
        return self._parent.__getattr__(self._type).__getattr__(name)

    def _add_object_name(self, name):
        self._names.append(name)

    def get_object_names(self):
        return self._names

    def info(self):
        return get_object_info(self._shop_api, self._type)

    def __iter__(self):
        return ModelBuilderObjectIterator(self)


class AttributeBuilderObject(object):
    def __init__(self, shop_api, object_type, object_name):
        self._shop_api = shop_api
        self._type = object_type
        self._name = object_name
        self._attr_names = list(shop_api.GetObjectTypeAttributeNames(object_type))
        self._attr_types = list(shop_api.GetObjectTypeAttributeDatatypes(object_type))
        self.datatype_dict = dict(zip(self._attr_names, self._attr_types))

    def __getattr__(self, attr_name):
        # Recursion guard
        if is_private_attr(attr_name):
            return

        if attr_name in self._attr_names:
            return AttributeObject(self._shop_api, self._type, self._name, attr_name, self.datatype_dict[attr_name])
        elif attr_name == 'generators' and self._type == 'plant':
            return self._get_generators()
        elif attr_name == 'unit_combinations' and self._type == 'plant':
            return self._get_unit_combinations()
        else:
            raise ValueError(f'Unknown attribute: "{attr_name}" for "{self._name}" ({self._type})')

    def __dir__(self):
        dirs = [x for x in super().__dir__() if x[0] != '_'] + self._attr_names
        if self._type == 'plant':
            return dirs + ['generators']
        else:
            return dirs

    def __getitem__(self, item):
        return self.__getattr__(item)

    def _get_generators(self):
        object_names = self._shop_api.GetObjectNamesInSystem()
        generator_indices = self._shop_api.GetRelations(self._type, self._name, 'generator_of_plant')
        gen_names = [object_names[i] for i in generator_indices]
        gen_objects = []
        for gen_name in gen_names:
            new_gen = AttributeBuilderObject(self._shop_api, 'generator', gen_name)
            gen_objects.append(new_gen)
        return gen_objects

    def _get_unit_combinations(self):
        object_names = self._shop_api.GetObjectNamesInSystem()
        comb_indices = self._shop_api.GetRelations(self._type, self._name, 'unit_combination_of_plant')
        comb_names = [object_names[i] for i in comb_indices]
        comb_objects = []
        for comb_name in comb_names:
            new_comb = AttributeBuilderObject(self._shop_api, 'unit_combination', comb_name)
            comb_objects.append(new_comb)
        return comb_objects

    def get_relations(self, direction="both", relation_type="all", relation_category='both'):
        direction = direction.lower()
        relation_type = relation_type.lower()
        relation_category = relation_category.lower()
        if direction not in ["both", "input", "output"]:     
            raise ValueError('Unknown direction, valid values are "both", "input" and "output"')
        if relation_category not in ["both", "physical", "logical"]:
            raise ValueError('Unknown relation_category, valid values are "both", "physical" and "logical"')
        object_names = self._shop_api.GetObjectNamesInSystem()
        object_types = self._shop_api.GetObjectTypesInSystem()
        if relation_type == "all":
            relation_types = self._shop_api.GetValidRelationTypes(self._type)
        else:
            relation_types = [relation_type]

        obj_list = []
        if direction == "input" or direction == "both":
            for relation_type in relation_types:
                input_relations = self._shop_api.GetInputRelations(self._type, self._name, relation_type)
                for object_index in input_relations:
                    # Filter out connections with wrong relation_category
                    from_type = object_types[object_index]
                    category = self._shop_api.GetRelationInfo(from_type, self._type, "relationCategory")
                    if relation_category != "both" and relation_category != category:
                        continue

                    # Build AttributeBuilderObject to represent the connected object and add to returned list
                    rel_object = AttributeBuilderObject(self._shop_api, object_types[object_index],
                                                        object_names[object_index])
                    obj_list.append(rel_object)
        if direction == "output" or direction == "both":
            for relation_type in relation_types:
                output_relations = self._shop_api.GetRelations(self._type, self._name, relation_type)
                for object_index in output_relations:
                    # Filter out connections with wrong relation_category
                    to_type = object_types[object_index]
                    category = self._shop_api.GetRelationInfo(self._type, to_type, "relationCategory")
                    if relation_category != "both" and relation_category != category:
                        continue

                    # Ignore a connection if it has already been seen. This happens for logical connections when the
                    # direction == 'both', since their bidirectional nature will ensure that they are already added
                    # in the 'input' loop above
                    if direction == "both" and category == "logical":
                        continue

                    # Build AttributeBuilderObject to represent the connected object and add to returned list
                    rel_object = AttributeBuilderObject(self._shop_api, object_types[object_index],
                                                        object_names[object_index])
                    obj_list.append(rel_object)
        return obj_list

    def connect(self, connection_type=''):
        connection_type = connection_type.lower()
        return ConnectToObjectType(self._shop_api, self._type, self._name, connection_type)

    def connect_to(self, related_object, connection_type=''):
        connection_type = connection_type.lower()
        if not connection_type:
            connection_type = self._shop_api.GetDefaultRelationType(self._type, related_object.get_type())
        else:
            if connection_type == "spill":
                connection_type = "connection_spill"
            elif connection_type == "bypass":
                connection_type = "connection_bypass"
            elif connection_type == "standard":
                connection_type = "connection_standard"
            else:
                raise ValueError(f'Unknown connection type: "{connection_type}"\nPyShop will use default connection '
                                 f'types if none are provided. Provided values can be "spill" or "bypass"')
        self._shop_api.AddRelation(self._type, self._name, connection_type, related_object.get_type(),
                                   related_object.get_name())

    def get_name(self):
        return self._name

    def get_type(self):
        return self._type


class AttributeObject(object):
    def __init__(self, shop_api, object_type, name, attr_name, attr_datatype):
        self._shop_api = shop_api
        self._type = object_type
        self._name = name
        self._attr_name = attr_name
        self._attr_datatype = attr_datatype

    def __getattr__(self, call):
        # Recursion guard
        if is_private_attr(call):
            return

        if call == 'get':
            if self._attr_datatype == 'xyt' and call == 'get':
                return self._get_xyt
            else:
                return self._get
        else:
            raise AttributeError()

    def __dir__(self):
        return [x for x in super().__dir__() if x[0] != '_'] + ['get']

    def __getitem__(self, item):
        return self.__getattr__(item)

    def _get(self):
        return get_attribute_value(self._shop_api, self._name, self._type, self._attr_name, self._attr_datatype)

    def _get_xyt(self, start_time=None, end_time=None):
        if start_time and end_time:
            return get_xyt_attribute(self._shop_api, self._name, self._type, self._attr_name, start_time, end_time)
        else:
            return get_attribute_value(self._shop_api, self._name, self._type, self._attr_name, self._attr_datatype)

    def set(self, value):
        set_attribute(self._shop_api, self._name, self._type, self._attr_name, self._attr_datatype, value)

    def help(self):
        print(self._shop_api.GetAttributeInfo(self._type, self._attr_name, 'description'))

    def web_help(self):
        url = self._shop_api.GetAttributeInfo(self._type, self._attr_name, 'documentationUrl')
        if not url:
            print("Could not find attribute type")
            return
        opened = webbrowser.open(url)
        if not opened:
            print("Could not open browser, documentation can be found at {}".format(url))

    def web_example(self):
        url_prefix = self._shop_api.GetAttributeInfo(self._type, self._attr_name, 'exampleUrlPrefix')
        example = self._shop_api.GetAttributeInfo(self._type, self._attr_name, 'example')
        if not example:
            print("Attribute does not currently have an associated example")
            return
        opened = webbrowser.open(url_prefix + example)
        if not opened:
            print("Could not open browser, documentation can be found at {}".format(url_prefix + example))

    def info(self):
        return get_attribute_info(self._shop_api, self._type, self._attr_name)


class ConnectToObjectType(object):
    def __init__(self, shop_api, from_type, from_name, connection_type):
        self._shop_api = shop_api
        self._from_type = from_type
        self._from_name = from_name
        self._connection_type = connection_type

    def __getattr__(self, object_type):
        # Recursion guard
        if is_private_attr(object_type):
            return

        return ConnectToObject(self._shop_api, self._from_type, self._from_name, self._connection_type, object_type)
        # print('Get item: '+str(item))

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __dir__(self):
        to_type = []
        if self._connection_type == '':
            if self._from_type == 'reservoir':
                to_type = ['plant', 'gate', 'junction', 'creek_intake']
            elif self._from_type == 'plant':
                to_type = ['reservoir', 'junction', 'generator', 'pump']
            elif self._from_type == 'gate':
                to_type = ['reservoir', 'junction']
            elif self._from_type == 'junction':
                to_type = ['plant', 'junction']
            elif self._from_type == 'creek_intake':
                to_type = ['junction']
            elif self._from_type == 'generator':
                to_type = ['needle_comb']
        elif self._connection_type == 'bypass':
            to_type = ['gate']
        elif self._connection_type == 'spill':
            to_type = ['gate']
        return to_type


class ConnectToObject(object):
    def __init__(self, shop_api, from_type, from_name, connection_type, object_type):
        # print('init connect to obj from: '+ from_type + ' ' + from_name + ' ' + type)
        self._shop_api = shop_api
        self._type = object_type
        self._from_type = from_type
        self._from_name = from_name
        self._connection_type = connection_type
        self._names = [n for n, t in zip(self._shop_api.GetObjectNamesInSystem(),
                                         self._shop_api.GetObjectTypesInSystem()) if t == object_type]

    def __dir__(self):
        return [x for x in super().__dir__() if x[0] != '_'] + self._names

    def __getattr__(self, name):
        # Recursion guard
        if is_private_attr(name):
            return

        return Connection(self._shop_api, self._from_type, self._from_name, self._connection_type, self._type, name)

    def __getitem__(self, item):
        return self.__getattr__(item)


class Connection(object):
    def __init__(self, shop_api, from_type, from_name, connection_type, to_type, to_name):
        self._shop_api = shop_api
        self._from_type = from_type
        self._from_name = from_name
        self._connection_type = connection_type
        self._to_name = to_name
        self._to_type = to_type

    def add(self):
        if not self._connection_type:
            connection_type = self._shop_api.GetDefaultRelationType(self._from_type, self._to_type)
        else:
            if self._connection_type == "spill":
                connection_type = "connection_spill"
            elif self._connection_type == "bypass":
                connection_type = "connection_bypass"
            elif self._connection_type == "standard":
                connection_type = "connection_standard"
            else:
                raise ValueError(f'Unknown connection type: "{self._connection_type}"\nPyShop will use default '
                                 f'connection types if none are provided. Provided values can be "spill" or "bypass"')
        self._shop_api.AddRelation(self._from_type, self._from_name, connection_type, self._to_type, self._to_name)
