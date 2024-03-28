from time import sleep


class Test:

    def __init__(self, a, b):
        self.a = a
        self.b = b

    @property
    def add(self):
        self.a = self.a + self.b
        print(self.a, self.b)

    def run(self):
        while True:
            sleep(1)
            self.add


if __name__ == "__main__":
    Test(1, 2).run()
