#! /bin/bash
echo "#######################################################"
echo "##### Install Geckolib library"
geckoLibExist=`sudo locate geckolib | wc -l || echo "nok"`
if [ "${socat_ver}" = "nok" ]; then
  sudo pip install geckolib
else
  echo "Geckolib is already installed, nothing to do"
fi


#popd > /dev/null

exit