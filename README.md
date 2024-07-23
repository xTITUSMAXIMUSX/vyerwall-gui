# Vyerwall-GUI for use with Vyos
The vyerwall-gui project is not affiliated with VyOS in any way. It is a wholly separate project to build a community tool that helps to visually build and manage firewall specific configurations for VyOS firewalls. This project is not owned by VyOS.io, or Sentrium S.L., nor does it seek to appear to be an official project, product or partner of the aforementioned.

# Using docker
1. Clone the repo
2. cd into the vyverwall-gui directory
3. run `docker build -t vyverwall-gui .`
4. run `docker run -d -p 5000:5000 --name vyerwall-gui -v /path/to/db:/app/var/app-instance vyerwall-gui`
5. Navigate to http://ip-address:5000
6. Default user/pass is `admin`
