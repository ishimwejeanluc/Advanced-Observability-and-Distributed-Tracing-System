pipeline {
    agent any 

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
        timeout(time: 1, unit: 'HOURS')
    }

    environment {
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {

        stage('Load .env') {
            steps {
                withCredentials([file(credentialsId: 'app_env_file1', variable: 'APP_ENV_FILE')]) {
                    sh '''
                        cp "$APP_ENV_FILE" .env
                        chmod 600 .env
                    '''

                    script {
                        def props = readProperties file: '.env'

                        def requiredKeys = [
                            'DOCKER_HUB_USER',
                            'DOCKER_HUB_PASSWORD',
                            'DOCKER_HUB_REPO',
                            'EC2_PUBLIC_IP',
                            'DB_HOST',
                            'DB_PORT',
                            'DB_NAME',
                            'DB_USER',
                            'DB_PASSWORD',
                            'GF_ADMIN_USER',
                            'GF_ADMIN_PASSWORD'
                        ]

                        def missingKeys = requiredKeys.findAll { key -> !props[key]?.trim() }
                        if (missingKeys) {
                            error("Missing required .env values: ${missingKeys.join(', ')}")
                        }

                        props.each { key, value ->
                            env."${key}" = value?.toString()?.trim()
                        }

                        // Standardized Docker credentials
                        env.DOCKER_USERNAME = env.DOCKER_HUB_USER
                        env.DOCKER_PASSWORD = env.DOCKER_HUB_PASSWORD

                        env.DOCKER_IMAGE = "${env.DOCKER_USERNAME}/${env.DOCKER_HUB_REPO}"
                    }
                }
            }
        }

        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                checkout scm
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building Docker image...'
                sh "docker build -t ${env.DOCKER_IMAGE}:${env.IMAGE_TAG} -f web/Dockerfile web"
            }
        }

        stage('Push to Registry') {
            steps {
                echo 'Pushing Docker image...'
                sh '''
                    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
                    docker push $DOCKER_IMAGE:$IMAGE_TAG
                '''
            }
        }

        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2_ssh2',
                        keyFileVariable: 'ANSIBLE_SSH_KEY',
                        usernameVariable: 'ANSIBLE_SSH_USER'
                    )
                ]) {
                    sh """
                    ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
                        -i "${env.EC2_PUBLIC_IP}," \
                        -u "${env.ANSIBLE_SSH_USER}" \
                        --private-key "${ANSIBLE_SSH_KEY}" \
                        ansible/main.yml \
                        -e "web_image=${env.DOCKER_IMAGE}:${env.IMAGE_TAG}" \
                        -e "docker_username=${env.DOCKER_USERNAME}" \
                        -e "docker_password=${env.DOCKER_PASSWORD}" \
                        -e "db_host=${env.DB_HOST}" \
                        -e "db_port=${env.DB_PORT}" \
                        -e "db_name=${env.DB_NAME}" \
                        -e "db_user=${env.DB_USER}" \
                        -e "db_password=${env.DB_PASSWORD}" \
                        -e "gf_admin_user=${env.GF_ADMIN_USER}" \
                        -e "gf_admin_password=${env.GF_ADMIN_PASSWORD}"
                    """
                }
            }
        }

        stage('Cleanup') {
            steps {
                sh 'docker image prune -f || true'
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo "Pipeline completed successfully."
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
    }
}