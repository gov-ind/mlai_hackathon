from opennem import OpenNEMClient

c = OpenNEMClient(base_url='https://api.opennem.org.au/networks')

print(dir(c))

for n in c.networks():
    print('kkk')
    print(n)

print(c.price('nem'))