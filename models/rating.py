class Rating:
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.values = []
        self.average = 0.0

    def add_value(self, value):
        self.values.append(value)
        self.average = sum(self.values) / len(self.values) if self.values else 0

    def to_dict(self):
            return {
                "id": self.id,
                "title": self.title,
                "values": self.values,
                "average": self.average
            }
